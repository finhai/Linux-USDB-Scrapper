"""Application controller: the only frontend entry to backend operations."""

import asyncio
import logging
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from usdb_scrapper.controllers.gateway import Gateway
from usdb_scrapper.controllers.runtime import Runtime, blocking
from usdb_scrapper.credential_manager import Credentials, CredentialStore, CredentialStoreError
from usdb_scrapper.credential_manager.provider import RememberedCredentials
from usdb_scrapper.domain import SongEntry
from usdb_scrapper.domain.download_item import DownloadItem
from usdb_scrapper.download_manager import BundleWorker, DownloadQueue
from usdb_scrapper.download_manager.sources import DownloadSources
from usdb_scrapper.download_manager.youtube import YtDlpDownloader
from usdb_scrapper.normalization.search import normalize_search_input
from usdb_scrapper.parser import ParsedTxt
from usdb_scrapper.storage_manager.library import Library
from usdb_scrapper.storage_manager.settings import Settings, SettingsError, SettingsStore
from usdb_scrapper.usdb_client import AuthenticationError, SearchQuery, SortDirection, SortField
from usdb_scrapper.usdb_client.search import SortState

logger = logging.getLogger(__name__)


class ApplicationController(QObject):
    results = Signal(object, bool)
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
        self._queue: DownloadQueue | None = None
        self._stages: dict[int, str] = {}
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
        self._queue = DownloadQueue(self._download, limit=self.settings.concurrency)
        self._poll_task = asyncio.create_task(self._poll())

    async def _poll(self) -> None:
        while True:
            if self._queue:
                self.downloads.emit(self._queue.snapshots(), dict(self._stages))
            await asyncio.sleep(0.25)

    async def _gateway(self) -> Gateway | None:
        provider = RememberedCredentials(enabled=self.settings.remember)
        if self._credentials is None:
            self._credentials = await blocking(lambda cancel: provider.get_credentials())
        if self._credentials is None:
            self.login_required.emit()
            return None
        return Gateway(self._credentials, provider)

    def login(self, username: str, password: str, remember: bool) -> None:
        self.runtime.submit(self._login(username, password, remember))

    async def _login(self, username: str, password: str, remember: bool) -> None:
        try:
            credentials = Credentials(username, password)
            gateway = Gateway(credentials, RememberedCredentials(enabled=remember))
            await blocking(lambda cancel: gateway.verify())
            self._credentials = credentials
            self.settings = replace(self.settings, remember=remember)
            try:
                await blocking(lambda cancel: self.settings_store.save(self.settings))
                if remember:
                    await blocking(lambda cancel: CredentialStore().save(credentials))
                else:
                    await blocking(lambda cancel: CredentialStore().forget())
            except (CredentialStoreError, SettingsError):
                self.message.emit(
                    "Signed in for this session; preferences or keyring could not be saved."
                )
            self.settings_changed.emit()
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

    def enqueue(self, songs: list[SongEntry]) -> None:
        self.runtime.submit(self._enqueue(songs))

    async def _enqueue(self, songs: list[SongEntry]) -> None:
        if self._queue is None or self._closing:
            return
        for song in songs:
            try:
                self._queue.enqueue(
                    DownloadItem(
                        song=song, bundle=Library(Path(self.settings.storage_root)).bundle(song)
                    )
                )
            except (ValueError, OSError):
                self.message.emit("Song is already queued or its library path is unavailable.")

    async def _download(self, item: DownloadItem) -> None:
        gateway = await self._gateway()
        if gateway is None:
            raise AuthenticationError("Sign in before retrying this download")

        async def txt(song_id: int) -> ParsedTxt:
            return await blocking(lambda cancel: gateway.txt(song_id, cancel))

        async def cover(song: ParsedTxt, target: Path) -> None:
            await blocking(lambda cancel: gateway.cover(item.song.song_id, target, cancel))

        source = DownloadSources(txt, YtDlpDownloader(), cover)
        worker = BundleWorker(
            source, progress=lambda song_id, stage: self._stages.update({song_id: stage})
        )
        await worker(item)

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
            self.message.emit("Remembered credentials removed.")
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
