import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest

from usdb_scrapper.controllers import gateway as module
from usdb_scrapper.domain.download_item import DownloadBundle
from usdb_scrapper.download_manager.sources import DownloadSources
from usdb_scrapper.parser import parse_txt
from usdb_scrapper.storage_manager.bundle import BundleStage


def text(meta):
    return f"#TITLE:T\n#ARTIST:A\n#MP3:old.mp3\n#BPM:120\n#VIDEO:{meta}\n: 0 4 2 note\nE\n"


def test_audio_tag_routes_separate_sources(tmp_path):
    song = parse_txt(text("co=cover.jpg,a=abcdefghijk,v=12345678901"))
    calls = []

    class Media:
        async def audio(self, url, target):
            calls.append(("audio", url))

        async def video(self, url, target):
            calls.append(("video", url))

    async def unused(*args):
        pass

    async def run():
        source = DownloadSources(unused, Media(), unused)
        await source.fetch_audio(song, tmp_path / "song.mp3")
        await source.fetch_video(song, tmp_path / "song.mp4")

    asyncio.run(run())
    assert calls == [
        ("audio", "https://www.youtube.com/watch?v=abcdefghijk"),
        ("video", "https://www.youtube.com/watch?v=12345678901"),
    ]


def test_audio_only_tag_uses_its_own_youtube_source():
    song = parse_txt(text("a=abcdefghijk,co=cover.jpg,medley=100-200"))
    assert song.audio_source == song.song.video == "https://www.youtube.com/watch?v=abcdefghijk"
    assert song.song.note_block == ": 0 4 2 note\nE\n"


def test_txt_countdowns_do_not_overlap(monkeypatch):
    active = 0
    maximum = 0
    lock = threading.Lock()

    @contextmanager
    def session(self):
        yield object()

    class Client:
        def __init__(self, session, pause):
            pass

        def retrieve_text(self, song_id):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.03)
            with lock:
                active -= 1
            return text("v=abcdefghijk")

    monkeypatch.setattr(module.Gateway, "session", session)
    monkeypatch.setattr(module, "TxtClient", Client)
    gateway = module.Gateway(None, None)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda sid: gateway.txt(sid, threading.Event()), [1, 2, 3]))
    assert len(results) == 3
    assert maximum == 1


def test_cancel_while_waiting_for_txt_lock(monkeypatch):
    lock = threading.Lock()
    monkeypatch.setattr(module, "_TXT_LOCK", lock)
    cancel = threading.Event()
    cancel.set()
    with lock:
        with pytest.raises(module.OperationCancelled):
            module.Gateway(None, None).txt(1, cancel)


@pytest.mark.parametrize("publish", [True, False])
def test_no_locks_or_partial_files_in_artist_directory(tmp_path, publish):
    artist = tmp_path / "library" / "Artist"
    directory = artist / "Song"
    bundle = DownloadBundle(
        txt=directory / "s.txt",
        audio=directory / "s.mp3",
        video=directory / "s.mp4",
        cover=directory / "s.jpg",
    )
    stage = BundleStage(bundle)
    if publish:
        for path in stage.paths.values():
            path.write_bytes(b"fixture")
        stage.publish()
    else:
        stage.discard()
    assert list(artist.iterdir()) == ([directory] if publish else [])
    assert list(artist.parent.iterdir()) == [artist]
    assert (tmp_path / "app-state" / "usdb-scrapper" / "locks").is_dir()
