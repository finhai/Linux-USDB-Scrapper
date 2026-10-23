"""One logical four-file operation, independent of media-download implementation."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from usdb_scrapper.domain.download_item import DownloadItem, DownloadState
from usdb_scrapper.download_manager.media import MediaDownloadError
from usdb_scrapper.parser import LocalMedia, ParsedTxt, serialize_v1_txt
from usdb_scrapper.storage_manager.bundle import BundleStage


class BundleDownloadError(Exception):
    """A bundle failed; partial output is not a completed library entry."""


class BundleSource(Protocol):
    """Async adapters must not block the event loop or retain shared HTTP sessions."""

    async def fetch_txt(self, song_id: int) -> ParsedTxt: ...
    async def fetch_audio(self, song: ParsedTxt, target: Path) -> None: ...
    async def fetch_video(self, song: ParsedTxt, target: Path) -> None: ...
    async def fetch_cover(self, song: ParsedTxt, target: Path) -> None: ...


class BundleWorker:
    """Queue worker: complete all transfers, serialize local TXT, verify, publish.

    Adapters write exactly the given paths and validate downloaded formats.
    Completion verifies presence/nonzero sizes, not that media is decodable.
    Storage stages replacements and restores existing files on failure.
    """

    def __init__(self, source: BundleSource, *, progress: Callable[[int, str], None] | None = None):
        self._source = source
        self._progress = progress or (lambda song_id, stage: None)

    async def __call__(self, item: DownloadItem) -> None:
        if item.state is not DownloadState.DOWNLOADING:
            raise BundleDownloadError("Bundle worker requires a downloading item")
        operation = "Preparing library files"
        stage: BundleStage | None = None
        try:
            stage = BundleStage(item.bundle)
            operation = "Retrieving TXT"
            self._progress(item.song.song_id, operation)
            parsed = await self._source.fetch_txt(item.song.song_id)
            paths = stage.paths
            # Validate export before spending time downloading media.
            operation = "Exporting TXT"
            data = serialize_v1_txt(
                parsed,
                LocalMedia(
                    audio=paths["audio"].name,
                    video=paths["video"].name,
                    cover=paths["cover"].name,
                ),
            )
            operation = "Downloading audio"
            self._progress(item.song.song_id, operation)
            await self._source.fetch_audio(parsed, paths["audio"])
            operation = "Downloading video"
            self._progress(item.song.song_id, operation)
            await self._source.fetch_video(parsed, paths["video"])
            operation = "Downloading cover"
            self._progress(item.song.song_id, operation)
            await self._source.fetch_cover(parsed, paths["cover"])
            operation = "Writing TXT"
            paths["txt"].write_bytes(data)
            operation = "Publishing bundle"
            self._progress(item.song.song_id, operation)
            stage.publish()
        except asyncio.CancelledError:
            raise
        except MediaDownloadError as error:
            raise BundleDownloadError(f"{operation}: {error.reason.value}") from None
        except Exception:
            raise BundleDownloadError(f"{operation} failed; retry the download") from None
        finally:
            if stage is not None:
                try:
                    stage.discard()
                except OSError:
                    raise BundleDownloadError("Partial bundle cleanup failed") from None
