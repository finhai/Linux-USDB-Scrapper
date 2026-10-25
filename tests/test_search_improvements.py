import asyncio
import threading
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt

from usdb_scrapper.controllers import application as module
from usdb_scrapper.controllers import gateway as gateway_module
from usdb_scrapper.controllers.search_cache import SearchCache
from usdb_scrapper.credential_manager import Credentials
from usdb_scrapper.domain import SongEntry
from usdb_scrapper.storage_manager.settings import Settings, SettingsStore
from usdb_scrapper.usdb_client import SearchQuery


def test_cache_expiry_is_not_extended_by_reads_and_capacity_is_bounded():
    now = [0.0]
    cache = SearchCache(2, ttl=10, clock=lambda: now[0])
    cache.put("a", 1)
    now[0] = 9
    assert cache.get("a") == 1
    now[0] = 10
    assert cache.get("a") is None
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") is None
    cache.clear()
    assert cache.get("c") is None


def test_listing_does_not_fetch_details_or_hide_unchecked_songs(monkeypatch):
    song = SongEntry(song_id=1, artist="A", title="T")

    class Session:
        def post_html(self, path, fields):
            assert fields["limit"] == "100"
            return "listing fixture"

    @contextmanager
    def session(self):
        yield Session()

    monkeypatch.setattr(gateway_module.Gateway, "session", session)
    monkeypatch.setattr(gateway_module, "parse_listing", lambda html: (song,))
    monkeypatch.setattr(
        gateway_module,
        "DetailClient",
        lambda session: (_ for _ in ()).throw(
            AssertionError("Detail request blocks initial results")
        ),
    )
    entries, more = gateway_module.Gateway(None, None).search_page(
        SearchQuery(artist="A"), 0, threading.Event()
    )
    assert entries == (song,)
    assert not more


def test_controller_first_results_cache_refresh_retry_and_cancellation(tmp_path, monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    assert app
    calls = []
    slow_entered = threading.Event()
    sources_entered = threading.Event()
    source_release = threading.Event()
    failures = [True]

    class Gateway:
        def __init__(self, *args):
            pass

        def search_page(self, query, offset, cancel):
            calls.append((query.artist, offset))
            if query.artist == "slow":
                slow_entered.set()
                cancel.wait(5)
                return (SongEntry(song_id=999, artist="Stale", title="Stale"),), False
            if offset == 100 and failures[0]:
                failures[0] = False
                raise OSError("synthetic network failure")
            return (SongEntry(song_id=offset + 1, artist=query.artist, title="Song"),), offset == 0

        def check_sources(self, songs, cancel, report):
            sources_entered.set()
            while not source_release.is_set():
                if cancel.wait(0.01):
                    return
            for song in songs:
                report(song.song_id, "Check on download")

        @staticmethod
        def cover_bytes(song_id, cancel):
            raise ValueError("no fixture cover")

    monkeypatch.setattr(module, "Gateway", Gateway)
    settings = SettingsStore(Path(tmp_path / "settings.json"))
    settings.save(Settings(storage_root=str(tmp_path / "library"), remember=False))
    controller = module.ApplicationController(settings)
    seen = []
    errors = []
    controller.results.connect(
        lambda rows, more: seen.extend(row.song_id for row in rows),
        Qt.ConnectionType.DirectConnection,
    )
    controller.search_reset.connect(seen.clear, Qt.ConnectionType.DirectConnection)
    controller.search_failed.connect(errors.append, Qt.ConnectionType.DirectConnection)

    async def run():
        controller._credentials = Credentials("fixture", "synthetic")
        await controller._search("fast", "", "id", "asc")
        assert seen == [1]  # Results appear while the source worker is still blocked.
        assert await asyncio.to_thread(sources_entered.wait, 2)
        await controller._load_page()
        assert errors and seen == [1]
        assert controller._offset == 100  # Failure does not advance pagination.
        await controller._load_page()
        assert seen == [1, 101] and not controller._more
        await controller._search("fast", "", "id", "asc")
        assert calls.count(("fast", 0)) == 1
        await controller._search("fast", "", "id", "asc", refresh=True)
        assert calls.count(("fast", 0)) == 2
        old = asyncio.create_task(controller._search("slow", "", "id", "asc"))
        assert await asyncio.to_thread(slow_entered.wait, 2)
        await controller._search("new", "", "id", "asc")
        await asyncio.gather(old, return_exceptions=True)
        assert seen == [1] and 999 not in seen
        assert controller._query.artist == "new"
        await controller._cancel_search()
        assert not controller._searching
        source_release.set()

    try:
        controller.runtime.submit(run()).result(timeout=15)
    finally:
        source_release.set()
        controller.runtime.submit(controller._shutdown()).result(timeout=10)
        controller.runtime.thread.join(5)
