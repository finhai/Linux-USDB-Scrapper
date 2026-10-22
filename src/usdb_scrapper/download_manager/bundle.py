"""One logical four-file operation, independent of media-download implementation."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from usdb_scrapper.domain.download_item import DownloadItem, DownloadState
from usdb_scrapper.parser import LocalMedia, ParsedTxt, serialize_v2_txt
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
    Storage supports new directories only. Existing entries fail unchanged.
    """

    def __init__(self, source: BundleSource, *, progress: Callable[[int, str], None] | None = None):
        self._source = source
        self._progress = progress or (lambda song_id, stage: None)

    async def __call__(self, item: DownloadItem) -> None:
        if item.state is not DownloadState.DOWNLOADING:
            raise BundleDownloadError("Bundle worker requires a downloading item")
        stage: BundleStage | None = None
        try:
            stage = BundleStage(item.bundle)
            self._progress(item.song.song_id, "Retrieving TXT")
            parsed = await self._source.fetch_txt(item.song.song_id)
            paths = stage.paths
            # Validate export before spending time downloading media.
            data = serialize_v2_txt(
                parsed,
                LocalMedia(
                    audio=paths["audio"].name,
                    video=paths["video"].name,
                    cover=paths["cover"].name,
                ),
            )
            self._progress(item.song.song_id, "Downloading audio")
            await self._source.fetch_audio(parsed, paths["audio"])
            self._progress(item.song.song_id, "Downloading video")
            await self._source.fetch_video(parsed, paths["video"])
            self._progress(item.song.song_id, "Downloading cover")
            await self._source.fetch_cover(parsed, paths["cover"])
            paths["txt"].write_bytes(data)
            self._progress(item.song.song_id, "Publishing bundle")
            stage.publish()
        except asyncio.CancelledError:
            raise
        except Exception:
            raise BundleDownloadError("Four-file bundle could not be completed") from None
        finally:
            if stage is not None:
                try:
                    stage.discard()
                except OSError:
                    raise BundleDownloadError("Partial bundle cleanup failed") from None
