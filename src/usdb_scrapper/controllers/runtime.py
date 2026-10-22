"""Dedicated asyncio thread; Qt UI communicates using queued signals."""

import asyncio
import threading
from collections.abc import Callable, Coroutine
from concurrent.futures import Future
from typing import Any


async def blocking[T](call: Callable[[threading.Event], T]) -> T:
    """Cooperatively stop and join a blocking worker before staging cleanup."""
    cancel = threading.Event()
    task = asyncio.create_task(asyncio.to_thread(call, cancel))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        cancel.set()
        try:
            await task
        except Exception:
            pass
        raise


class Runtime:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._tasks: set[asyncio.Task[None]] = set()
        self.thread = threading.Thread(target=self._run, name="usdb-worker", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        self.loop.run_until_complete(self.loop.shutdown_default_executor())
        self.loop.close()

    def submit(self, operation: Coroutine[Any, Any, None]) -> Future[None]:
        async def tracked() -> None:
            task = asyncio.current_task()
            assert task is not None
            self._tasks.add(task)
            try:
                await operation
            finally:
                self._tasks.discard(task)

        return asyncio.run_coroutine_threadsafe(tracked(), self.loop)

    async def cancel_others(self) -> None:
        tasks = self._tasks - {asyncio.current_task()}
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
