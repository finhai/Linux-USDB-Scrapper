import asyncio
from pathlib import PurePosixPath

import pytest

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.domain.download_item import DownloadBundle, DownloadItem, DownloadState
from usdb_scrapper.download_manager import DownloadQueue


def job(number):
    return DownloadItem(
        song=SongEntry(song_id=number, artist="Artist", title="Song"),
        bundle=DownloadBundle(
            **{
                kind: PurePosixPath(f"{number}/song.{suffix}")
                for kind, suffix in [
                    ("txt", "txt"),
                    ("audio", "mp3"),
                    ("video", "mp4"),
                    ("cover", "jpg"),
                ]
            }
        ),
    )


def test_excess_jobs_wait_fifo_and_never_exceed_limit():
    async def scenario():
        releases = {n: asyncio.Event() for n in range(1, 6)}
        started = asyncio.Queue()
        active = 0
        peak = 0

        async def worker(item):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            started.put_nowait(item.song.song_id)
            await releases[item.song.song_id].wait()
            active -= 1

        queue = DownloadQueue(worker, limit=2)
        try:
            for n in range(1, 6):
                queue.enqueue(job(n))
            assert [await started.get(), await started.get()] == [1, 2]
            assert [x.state for x in queue.snapshots()] == [DownloadState.DOWNLOADING] * 2 + [
                DownloadState.QUEUED
            ] * 3
            for finishing, next_id in [(1, 3), (2, 4), (3, 5)]:
                releases[finishing].set()
                assert await started.get() == next_id
            releases[4].set()
            releases[5].set()
            await queue.close()
            assert peak == 2
            assert all(x.state is DownloadState.COMPLETED for x in queue.snapshots())
        finally:
            for event in releases.values():
                event.set()
            await queue.close()

    asyncio.run(asyncio.wait_for(scenario(), 3))


def test_limit_changes_and_failures_release_capacity():
    async def scenario():
        releases = {n: asyncio.Event() for n in range(1, 5)}
        started = asyncio.Queue()

        async def worker(item):
            n = item.song.song_id
            started.put_nowait(n)
            await releases[n].wait()
            if n == 2:
                raise RuntimeError("private-secret")

        queue = DownloadQueue(worker, limit=1)
        try:
            for n in range(1, 5):
                queue.enqueue(job(n))
            assert await started.get() == 1
            queue.set_limit(2)
            assert await started.get() == 2
            queue.set_limit(1)
            releases[1].set()
            # Let task completion and its callback run; job 3 must remain queued.
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert queue.snapshots()[2].state is DownloadState.QUEUED
            releases[2].set()
            assert await started.get() == 3
            assert queue.snapshots()[1].error == "Download worker failed"
            releases[3].set()
            assert await started.get() == 4
        finally:
            for event in releases.values():
                event.set()
            await queue.close()

    asyncio.run(asyncio.wait_for(scenario(), 3))


def test_invalid_limit_duplicates_and_close():
    async def scenario():
        async def worker(item):
            pass

        for limit in (0, -1, True, 1.5):
            with pytest.raises(ValueError):
                DownloadQueue(worker, limit=limit)
        queue = DownloadQueue(worker)
        queue.enqueue(job(1))
        with pytest.raises(ValueError):
            queue.enqueue(job(1))
        await queue.close()
        with pytest.raises(RuntimeError):
            queue.enqueue(job(2))
        await queue.close()

    asyncio.run(asyncio.wait_for(scenario(), 3))


def test_cancel_active_and_queued_then_retry_cleanly():
    async def scenario():
        started = asyncio.Event()
        cleaned = asyncio.Event()
        attempts = 0

        async def worker(item):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    await asyncio.sleep(0)
                    cleaned.set()

        queue = DownloadQueue(worker, limit=1)
        queue.enqueue(job(1))
        queue.enqueue(job(2))
        await started.wait()
        queue.cancel(2)
        queue.cancel(1)
        queue.cancel(1)
        await queue.wait_idle()
        assert cleaned.is_set()
        assert all(x.state is DownloadState.CANCELLED for x in queue.snapshots())
        queue.retry(1)
        await queue.wait_idle()
        assert queue.snapshots()[0].state is DownloadState.COMPLETED
        assert attempts == 2
        with pytest.raises(ValueError):
            queue.retry(1)
        await queue.close()

    asyncio.run(asyncio.wait_for(scenario(), 3))


def test_cancel_all_does_not_start_pending_jobs():
    async def scenario():
        calls = []

        async def worker(item):
            calls.append(item.song.song_id)
            await asyncio.Event().wait()

        queue = DownloadQueue(worker, limit=1)
        for n in range(1, 5):
            queue.enqueue(job(n))
        await asyncio.sleep(0)
        await queue.cancel_all()
        assert calls == [1]
        assert all(x.state is DownloadState.CANCELLED for x in queue.snapshots())
        await queue.close()

    asyncio.run(asyncio.wait_for(scenario(), 3))
