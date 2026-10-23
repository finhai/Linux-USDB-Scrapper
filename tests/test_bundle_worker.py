import asyncio
from pathlib import PurePath

import pytest

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.domain.download_item import DownloadBundle, DownloadItem, DownloadState
from usdb_scrapper.download_manager import BundleWorker, DownloadQueue
from usdb_scrapper.parser import parse_txt


class Source:
    def __init__(self, fail=None, missing=None):
        self.fail, self.missing = fail, missing

    async def fetch_txt(self, song_id):
        if self.fail == "txt":
            raise RuntimeError("private error")
        return parse_txt(
            "#TITLE:T\n#ARTIST:A\n#BPM:120\n#MP3:old.mp3\n#VIDEO:v=abcdefghijk\n: 0 4 2 text\nE\n"
        )

    def write(self, kind, path):
        if self.fail == kind:
            path.write_bytes(b"partial")
            raise RuntimeError("private error")
        if self.missing != kind:
            path.write_bytes(b"synthetic media fixture")

    async def fetch_audio(self, song, target):
        self.write("audio", target)

    async def fetch_video(self, song, target):
        self.write("video", target)

    async def fetch_cover(self, song, target):
        self.write("cover", target)


def item(root):
    return DownloadItem(
        song=SongEntry(song_id=1, artist="A", title="T"),
        bundle=DownloadBundle(
            txt=PurePath(root / "song.txt"),
            audio=PurePath(root / "song.mp3"),
            video=PurePath(root / "song.mp4"),
            cover=PurePath(root / "cover.jpg"),
        ),
    )


def run(source, root):
    async def scenario():
        queue = DownloadQueue(BundleWorker(source))
        queue.enqueue(item(root))
        await queue.close()
        return queue.snapshots()[0]

    return asyncio.run(scenario())


def test_completion_means_all_four_files_exist(tmp_path):
    root = tmp_path / "song"
    result = run(Source(), root)
    assert result.state is DownloadState.COMPLETED
    assert {p.name for p in root.iterdir()} == {"song.txt", "song.mp3", "song.mp4", "cover.jpg"}
    song = parse_txt((root / "song.txt").read_text())
    assert (song.song.audio, song.song.video, song.song.cover) == (
        "song.mp3",
        "song.mp4",
        "cover.jpg",
    )
    assert song.song.version == "1.0.0"
    assert song.song.bpm == 120
    assert not list(tmp_path.glob(".usdb-partial-*"))


@pytest.mark.parametrize("kind", ["txt", "audio", "video", "cover"])
def test_failed_transfer_never_marks_partial_bundle_done(tmp_path, kind):
    root = tmp_path / "song"
    result = run(Source(fail=kind), root)
    assert result.state is DownloadState.FAILED
    assert "private" not in result.error
    operation = "Retrieving TXT" if kind == "txt" else f"Downloading {kind}"
    assert result.error == f"{operation} failed; retry the download"
    assert not root.exists()
    assert not list(tmp_path.glob(".usdb-partial-*"))


@pytest.mark.parametrize("kind", ["audio", "video", "cover"])
def test_adapter_return_without_file_is_failure(tmp_path, kind):
    root = tmp_path / "song"
    assert run(Source(missing=kind), root).state is DownloadState.FAILED
    assert not root.exists()


def test_existing_library_is_untouched(tmp_path):
    root = tmp_path / "song"
    root.mkdir()
    (root / "original.txt").write_text("keep")
    assert run(Source(), root).state is DownloadState.FAILED
    assert (root / "original.txt").read_text() == "keep"
    assert len(list(root.iterdir())) == 1


def test_cancellation_discards_staging(tmp_path):
    async def scenario():
        entered = asyncio.Event()

        class WaitingSource(Source):
            async def fetch_audio(self, song, target):
                target.write_bytes(b"partial")
                entered.set()
                await asyncio.Event().wait()

        root = tmp_path / "song"
        task = asyncio.create_task(
            BundleWorker(WaitingSource())(item(root).transition(DownloadState.DOWNLOADING))
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not root.exists()
        assert not list(tmp_path.glob(".usdb-partial-*"))

    asyncio.run(asyncio.wait_for(scenario(), 3))


def test_empty_file_cannot_complete_bundle(tmp_path):
    class EmptySource(Source):
        async def fetch_cover(self, song, target):
            target.touch()

    root = tmp_path / "song"
    assert run(EmptySource(), root).state is DownloadState.FAILED
    assert not root.exists()


def test_media_implementation_can_be_replaced_without_changing_bundle(tmp_path):
    from usdb_scrapper.download_manager.sources import DownloadSources

    class Media:
        async def audio(self, url, target):
            assert url == "https://www.youtube.com/watch?v=abcdefghijk"
            target.write_bytes(b"audio")

        async def video(self, url, target):
            target.write_bytes(b"video")

    class Replacement(Media):
        async def audio(self, url, target):
            target.write_bytes(b"replacement audio")

    async def run():
        source = Source()
        for index, media in enumerate((Media(), Replacement())):
            entry = item(tmp_path / str(index)).transition(DownloadState.DOWNLOADING)
            composed = DownloadSources(source.fetch_txt, media, source.fetch_cover)
            await BundleWorker(composed)(entry)
            assert (tmp_path / str(index) / "song.mp3").is_file()

    asyncio.run(run())


def test_safe_media_reason_reaches_queue(tmp_path):
    from usdb_scrapper.download_manager.media import MediaDownloadError, MediaFailure

    class FailedMedia(Source):
        async def fetch_video(self, song, target):
            raise MediaDownloadError("private URL", reason=MediaFailure.FORBIDDEN)

    result = run(FailedMedia(), tmp_path / "song")
    assert result.state is DownloadState.FAILED
    assert result.error == "Downloading video: YouTube refused the media request (403); retry later"
    assert "private" not in result.error
