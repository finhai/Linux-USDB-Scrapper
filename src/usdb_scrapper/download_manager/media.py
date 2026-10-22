"""Stable media boundary; no downloader-specific options escape this module."""

from pathlib import Path
from typing import Protocol


class MediaDownloadError(Exception):
    """Media retrieval or conversion failed."""


class MediaDownloader(Protocol):
    """Write a complete MP3 or MP4 at a new target, or raise.

    Implementations must be asynchronous and clean up on failure/cancellation.
    The caller owns the target directory and must serialize writes to each target.
    """

    async def audio(self, url: str, target: Path) -> None: ...
    async def video(self, url: str, target: Path) -> None: ...
