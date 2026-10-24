"""Application controller: the only frontend entry to backend operations."""

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import replace
from functools import partial
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from usdb_scrapper.controllers.gateway import Gateway
from usdb_scrapper.controllers.runtime import Runtime, blocking
from usdb_scrapper.credential_manager import Credentials, CredentialStore, CredentialStoreError
from usdb_scrapper.credential_manager.provider import RememberedCredentials
from usdb_scrapper.credential_manager.store import REMEMBER_SECONDS
from usdb_scrapper.domain import SongEntry
from usdb_scrapper.domain.download_item import DownloadItem
from usdb_scrapper.download_manager import BundleWorker, DownloadQueue
from usdb_scrapper.download_manager.sources import DownloadSources
from usdb_scrapper.download_manager.youtube import YtDlpDownloader
from usdb_scrapper.normalization.search import normalize_search_input
from usdb_scrapper.parser import ParsedTxt
from usdb_scrapper.storage_manager.legacy import cleanup_legacy
from usdb_scrapper.storage_manager.library import Library
from usdb_scrapper.storage_manager.settings import Settings, SettingsError, SettingsStore
from usdb_scrapper.usdb_client import AuthenticationError, SearchQuery, SortDirection, SortField
from usdb_scrapper.usdb_client.search import SortState

logger = logging.getLogger(__name__)


class ApplicationController(QObject):
    enqueue_result = Signal(object, str)
    results = Signal(object, bool)
    cover_ready = Signal(int, bytes)
    downloads = Signal(object, object)
    message = Signal(str)
    busy = Signal(bool)
    login_required = Signal()
    login_complete = Signal()
    stopped = Signal()
    settings_changed = Signal()

    def __init__(self, settings_store: SettingsStore | None = None) -> None:
        super().__init__()
        self.settings_store = settings_store or SettingsStore()
        self.startup_message = ""
        try:
            self.settings = self.settings_store.load()
        except SettingsError as exc:
            self.settings = Settings()
            self.startup_message = str(exc)
        self.runtime = Runtime(on_error=self._unexpected_error)
        self._credentials: Credentials | None = None
        self._login_expires_at: float | None = None
        self._queue: DownloadQueue | None = None
        self._stages: dict[int, str] = {}
        self._covers: OrderedDict[int, bytes] = OrderedDict()
        self._query: SearchQuery | None = None
        self._offset = 0
        self._more = False
        self._searching = False
        self._seen: set[int] = set()
        self._pending_search = False
        self._closing = False
        self._search_task: asyncio.Task[None] | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self.runtime.submit(self._initialize())

    def _unexpected_error(self) -> None:
        self.busy.emit(False)
        self.message.emit("Operation failed. Retry it; restart the application if it persists.")

    async def _initialize(self) -> None:
        try:
            recovered = await blocking(
                lambda cancel: Library(Path(self.settings.storage_root)).recover()
            )
            if recovered:
                self.message.emit(f"Recovered {recovered} interrupted library transactions.")
        except (ValueError, OSError):
            logger.warning("Library recovery needs inspection")
            self.message.emit("A library transaction needs inspection before retrying its song.")
        self._queue = DownloadQueue(
            self._download, limit=self.settings.concurrency, autostart=False
        )
        self._poll_task = asyncio.create_task(self._poll())

    async def _poll(self) -> None:
        while True:
            self._expire_login()
            if self._queue:
                self.downloads.emit(self._queue.snapshots(), dict(self._stages))
            await asyncio.sleep(0.25)

    def _expire_login(self) -> None:
        if self._login_expires_at is not None and time.time() >= self._login_expires_at:
            self._credentials = None
            self._login_expires_at = None
            self.message.emit("Your 30-day login has expired. Please sign in again.")
            self.login_required.emit()

    def restore_login(self) -> None:
        self.runtime.submit(self._restore_login())

    async def _restore_login(self) -> None:
        try:
            if not self.settings.remember:
                self.login_required.emit()
                return
            saved = await blocking(lambda cancel: CredentialStore().load_recent())
            if saved is None:
                self.login_required.emit()
                return
            credentials, expires_at = saved
            await blocking(
                lambda cancel: Gateway(credentials, RememberedCredentials(enabled=False)).verify()
            )
            if time.time() >= expires_at:
                self.login_required.emit()
                return
            self._credentials = credentials
            self._login_expires_at = expires_at
            self.login_complete.emit()
        except Exception:
            self.message.emit("Saved login unavailable. Please sign in again.")
            self.login_required.emit()

    async def _gateway(self) -> Gateway | None:
        self._expire_login()
        if self._credentials is None:
            self.login_required.emit()
            return None
        return Gateway(self._credentials, RememberedCredentials(enabled=False))

    def login(self, username: str, password: str, remember: bool) -> None:
        self.runtime.submit(self._login(username, password, remember))

    async def _login(self, username: str, password: str, remember: bool) -> None:
        try:
            credentials = Credentials(username, password)
            gateway = Gateway(credentials, RememberedCredentials(enabled=False))
            await blocking(lambda cancel: gateway.verify())
            self._credentials = credentials
            self._login_expires_at = time.time() + REMEMBER_SECONDS
            self.settings = replace(self.settings, remember=remember)
            try:
                await blocking(lambda cancel: self.settings_store.save(self.settings))
                if remember:
                    await blocking(lambda cancel: CredentialStore().save(credentials))
                else:
                    await blocking(lambda cancel: CredentialStore().forget())
            except (CredentialStoreError, SettingsError):
                self.message.emit("Signed in, but this login could not be remembered.")
            self.login_complete.emit()
            if self._pending_search:
                self._pending_search = False
                await self._load_page()
        except Exception:
            self.message.emit(
                "Login failed. Check your credentials and connection, then try again."
            )
            logger.warning("Login failed")
            self.login_required.emit()

    def search(self, artist: str, title: str, field: str, direction: str) -> None:
        self.runtime.submit(self._search(artist, title, field, direction))

    async def _search(self, artist: str, title: str, field: str, direction: str) -> None:
        if self._searching or self._closing:
            return
        try:
            self._query = SearchQuery(
                normalize_search_input(artist),
                normalize_search_input(title),
                SortState(SortField(field), SortDirection(direction)),
            )
        except (ValueError, TypeError):
            self.message.emit("Enter an artist or title and select a valid sort order.")
            return
        self._offset, self._more = 0, True
        self._seen.clear()
        await self._load_page()

    def load_more(self) -> None:
        self.runtime.submit(self._load_page())

    async def _load_page(self) -> None:
        if self._searching or not self._more or self._query is None or self._closing:
            return
        self._searching = True
        self._search_task = asyncio.current_task()
        self.busy.emit(True)
        try:
            gateway = await self._gateway()
            if gateway is None:
                self._pending_search = True
                return
            query, offset = self._query, self._offset
            if offset >= 10000:
                self._more = False
                raise ValueError("Search reached the page limit")
            entries, more = await blocking(
                lambda cancel: gateway.search_page(query, offset, cancel)
            )
            if self._seen.intersection(entry.song_id for entry in entries):
                raise ValueError("Search pages overlapped")
            self._seen.update(entry.song_id for entry in entries)
            self._offset += 100
            self._more = more
            self.results.emit(entries, more)
            self.runtime.submit(self._load_covers(entries))
            self.message.emit(f"Loaded {len(self._seen)} matching songs with YouTube links.")
        except AuthenticationError:
            self._credentials = None
            self._pending_search = True
            self.login_required.emit()
        except asyncio.CancelledError:
            raise
        except Exception:
            self.message.emit("Search failed. Check your connection and retry the search.")
            logger.warning("Search failed")
        finally:
            self._searching = False
            self._search_task = None
            self.busy.emit(False)

    async def _load_covers(self, songs: tuple[SongEntry, ...]) -> None:
        for song in songs:
            if self._closing:
                return
            data = self._covers.get(song.song_id)
            if data is None:
                try:
                    data = await blocking(partial(Gateway.cover_bytes, song.song_id))
                except Exception:
                    continue  # A missing preview must not hide a selectable song.
                self._covers[song.song_id] = data
                while sum(map(len, self._covers.values())) > 32_000_000:
                    self._covers.popitem(last=False)
            self.cover_ready.emit(song.song_id, data)

    def enqueue(self, songs: list[SongEntry]) -> None:
        self.runtime.submit(self._enqueue(songs))

    async def _enqueue(self, songs: list[SongEntry]) -> None:
        requested = [song.song_id for song in songs]
        if self._queue is None or self._closing:
            self.enqueue_result.emit(requested, "Queue unavailable. Please try again.")
            return
        existing = {item.song.song_id for item in self._queue.snapshots()}
        added = duplicate = failed = 0
        for song in songs:
            if song.song_id in existing:
                duplicate += 1
                continue
            try:
                self._queue.enqueue(
                    DownloadItem(
                        song=song, bundle=Library(Path(self.settings.storage_root)).bundle(song)
                    )
                )
                existing.add(song.song_id)
                added += 1
            except (ValueError, OSError):
                failed += 1
        self.downloads.emit(self._queue.snapshots(), dict(self._stages))
        parts = []
        if added:
            parts.append(f"Added {added} to queue. Open Downloads when ready to start.")
        if duplicate:
            parts.append(f"{duplicate} already in Downloads.")
        if failed:
            parts.append(f"Could not add {failed}: check the library location.")
        self.enqueue_result.emit(requested, " ".join(parts))

    async def _download(self, item: DownloadItem) -> None:
        gateway = await self._gateway()
        if gateway is None:
            raise AuthenticationError("Sign in before retrying this download")

        async def txt(song_id: int) -> ParsedTxt:
            return await blocking(lambda cancel: gateway.txt(song_id, cancel))

        async def cover(song: ParsedTxt, target: Path) -> None:
            cached = self._covers.get(item.song.song_id)
            if cached is not None:
                await blocking(lambda cancel: target.write_bytes(cached))
            else:
                await blocking(lambda cancel: gateway.cover(item.song.song_id, target, cancel))

        source = DownloadSources(txt, YtDlpDownloader(), cover)
        worker = BundleWorker(
            source, progress=lambda song_id, stage: self._stages.update({song_id: stage})
        )
        await worker(item)
        try:
            root = Path(item.bundle.txt).parent.parent.parent
            await blocking(lambda cancel: cleanup_legacy(root, item.song))
        except OSError:
            self.message.emit("Download completed; old download files could not be removed.")

    def start_downloads(self) -> None:
        self.runtime.submit(self._start_downloads())

    async def _start_downloads(self) -> None:
        if self._queue and not self._closing:
            self._queue.start_pending()

    def cancel(self, song_id: int) -> None:
        self.runtime.submit(self._control(song_id, False))

    def retry(self, song_id: int) -> None:
        self.runtime.submit(self._control(song_id, True))

    async def _control(self, song_id: int, retry: bool) -> None:
        if self._queue and not self._closing:
            try:
                if retry:
                    self._stages.pop(song_id, None)
                    self._queue.retry(song_id)
                else:
                    self._queue.cancel(song_id)
            except (ValueError, KeyError):
                self.message.emit("This download cannot perform that action in its current state.")

    def save_settings(
        self, root: str, concurrency: int, field: str, direction: str, remember: bool
    ) -> None:
        self.runtime.submit(self._save_settings(root, concurrency, field, direction, remember))

    async def _save_settings(
        self, root: str, concurrency: int, field: str, direction: str, remember: bool
    ) -> None:
        try:
            settings = Settings(root, concurrency, field, direction, remember)
            await blocking(lambda cancel: self.settings_store.save(settings))
            self.settings = settings
            self.settings_changed.emit()
            if self._queue:
                self._queue.set_limit(concurrency)
            self.message.emit("Settings saved. New downloads use the selected library location.")
        except (SettingsError, OSError):
            logger.warning("Settings save failed")
            self.message.emit("Settings could not be saved. Check the values and location.")

    def forget_credentials(self) -> None:
        self.runtime.submit(self._forget())

    async def _forget(self) -> None:
        try:
            await blocking(lambda cancel: CredentialStore().forget())
            self._credentials = None
            self._login_expires_at = None
            self.message.emit("Remembered credentials removed.")
            self.login_required.emit()
        except CredentialStoreError:
            logger.warning("Credential removal failed")
            self.message.emit("The native keyring could not remove the remembered credentials.")

    def shutdown(self) -> None:
        self.runtime.submit(self._shutdown())

    async def _shutdown(self) -> None:
        self._closing = True
        await self.runtime.cancel_others()
        if self._queue:
            await self._queue.cancel_all()
            await self._queue.close()
        if self._poll_task:
            self._poll_task.cancel()
            await asyncio.gather(self._poll_task, return_exceptions=True)
        self._credentials = None
        self.stopped.emit()
        self.runtime.stop()
