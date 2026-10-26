"""Event-loop-owned FIFO scheduling with a dynamically adjustable active limit."""

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from functools import partial

from usdb_scrapper.domain.download_item import DownloadItem, DownloadState
from usdb_scrapper.download_manager.bundle import BundleDownloadError


class DownloadQueue:
    """Schedule an injected bundle worker; create and use on one asyncio loop.

    A worker returns only after its whole bundle has completed or raises on
    failure. This queue does not download files, inspect bundles, or call Qt.
    Lowering the limit lets existing work finish and prevents new starts until
    the active count is below the new limit. Duplicate song IDs are rejected.
    """

    def __init__(
        self,
        worker: Callable[[DownloadItem], Awaitable[None]],
        *,
        limit: int = 2,
        autostart: bool = True,
    ):
        self._validate_limit(limit)
        self._loop = asyncio.get_running_loop()
        self._worker = worker
        self._limit = limit
        self._autostart = autostart
        self._ready: set[int] = set()
        self._items: dict[int, DownloadItem] = {}
        self._pending: deque[int] = deque()
        self._active: dict[int, asyncio.Task[None]] = {}
        self._idle = asyncio.Event()
        self._idle.set()
        self._closed = False

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("Concurrency limit must be a positive integer")

    def _check_loop(self) -> None:
        if asyncio.get_running_loop() is not self._loop:
            raise RuntimeError("Download queue belongs to another event loop")

    @property
    def limit(self) -> int:
        return self._limit

    def snapshots(self) -> tuple[DownloadItem, ...]:
        self._check_loop()
        return tuple(self._items.values())

    def enqueue(self, item: DownloadItem) -> None:
        self._check_loop()
        if self._closed:
            raise RuntimeError("Download queue is closed")
        if not isinstance(item, DownloadItem) or item.state is not DownloadState.QUEUED:
            raise ValueError("Only queued DownloadItems may be submitted")
        song_id = item.song.song_id
        if song_id in self._items:
            raise ValueError("Song is already in this queue")
        if any(
            existing.bundle.txt.parent == item.bundle.txt.parent
            for existing in self._items.values()
        ):
            raise ValueError("Another queued song uses the same artist/title folder")
        self._items[song_id] = item
        self._pending.append(song_id)
        self._idle.clear()
        self._pump()

    def cancel(self, song_id: int) -> None:
        """Cancel queued or active work; active cleanup finishes before terminal state."""
        self._check_loop()
        item = self._items[song_id]
        if item.state is DownloadState.QUEUED:
            self._pending.remove(song_id)
            self._ready.discard(song_id)
            self._items[song_id] = item.transition(DownloadState.CANCELLED)
            self._pump()
        elif item.state is DownloadState.DOWNLOADING:
            task = self._active[song_id]
            if not task.cancelling():
                task.cancel()

    def retry(self, song_id: int) -> None:
        self._check_loop()
        if self._closed:
            raise RuntimeError("Download queue is closed")
        item = self._items[song_id]
        if item.state not in (DownloadState.FAILED, DownloadState.CANCELLED):
            raise ValueError("Only failed or cancelled downloads can be retried")
        self._items[song_id] = item.transition(DownloadState.RETRY).transition(DownloadState.QUEUED)
        self._pending.append(song_id)
        self._idle.clear()
        self._pump()

    async def cancel_all(self) -> None:
        self._check_loop()
        # Cancel pending first, so completed active tasks cannot start another job.
        for song_id in tuple(self._pending):
            self.cancel(song_id)
        for song_id in tuple(self._active):
            self.cancel(song_id)
        await self.wait_idle()

    def set_limit(self, limit: int) -> None:
        self._check_loop()
        self._validate_limit(limit)
        if self._closed:
            raise RuntimeError("Download queue is closed")
        self._limit = limit
        self._pump()

    def start_pending(self) -> None:
        """Start the currently queued batch; later additions await another start."""
        self._check_loop()
        self._ready.update(self._pending)
        self._pump()

    def _pump(self) -> None:
        while self._pending and len(self._active) < self._limit:
            song_id = next(
                (sid for sid in self._pending if self._autostart or sid in self._ready), None
            )
            if song_id is None:
                break
            self._pending.remove(song_id)
            self._ready.discard(song_id)
            self._items[song_id] = self._items[song_id].transition(DownloadState.DOWNLOADING)
            task = self._loop.create_task(self._run(self._items[song_id]))
            self._active[song_id] = task
            task.add_done_callback(partial(self._finished, song_id))
        if not self._pending and not self._active:
            self._idle.set()

    async def _run(self, item: DownloadItem) -> None:
        await self._worker(item)

    def _finished(self, song_id: int, task: asyncio.Task[None]) -> None:
        self._active.pop(song_id)
        try:
            task.result()
        except asyncio.CancelledError:
            self._items[song_id] = self._items[song_id].transition(DownloadState.CANCELLED)
        except BundleDownloadError as error:
            self._items[song_id] = self._items[song_id].transition(
                DownloadState.FAILED, error=str(error)
            )
        except Exception:
            logging.getLogger(__name__).warning("Download failed; retry is available")
            # Worker errors may carry URLs/credentials. Only publish a generic state.
            self._items[song_id] = self._items[song_id].transition(
                DownloadState.FAILED, error="Download worker failed"
            )
        else:
            self._items[song_id] = self._items[song_id].transition(DownloadState.COMPLETED)
        self._pump()

    async def wait_idle(self) -> None:
        self._check_loop()
        await self._idle.wait()

    async def close(self) -> None:
        """Reject new submissions and drain accepted jobs; does not cancel them."""
        self._check_loop()
        self._closed = True
        await self.wait_idle()
