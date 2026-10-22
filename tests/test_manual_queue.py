import asyncio
from pathlib import PurePath

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.domain.download_item import DownloadBundle, DownloadItem, DownloadState
from usdb_scrapper.download_manager import DownloadQueue


def test_manual_start_does_not_include_later_additions():
    async def scenario():
        started = []
        gate = asyncio.Event()

        async def worker(item):
            started.append(item.song.song_id)
            await gate.wait()

        def item(song_id):
            return DownloadItem(
                song=SongEntry(song_id=song_id, artist="A", title="T"),
                bundle=DownloadBundle(
                    txt=PurePath("a.txt"),
                    audio=PurePath("a.mp3"),
                    video=PurePath("a.mp4"),
                    cover=PurePath("a.jpg"),
                ),
            )

        queue = DownloadQueue(worker, autostart=False)
        queue.enqueue(item(1))
        await asyncio.sleep(0)
        assert started == []
        queue.start_pending()
        await asyncio.sleep(0)
        assert started == [1]
        queue.enqueue(item(2))
        gate.set()
        for _ in range(4):
            await asyncio.sleep(0)
        assert started == [1]
        assert queue.snapshots()[1].state is DownloadState.QUEUED
        queue.start_pending()
        await queue.close()
        assert started == [1, 2]

    asyncio.run(scenario())
