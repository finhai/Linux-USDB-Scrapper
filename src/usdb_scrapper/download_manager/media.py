"""Stable media boundary; no downloader-specific options escape this module."""

from enum import Enum
from pathlib import Path
from typing import Protocol


class MediaFailure(Enum):
    UNKNOWN = "YouTube download failed; retry the download"
    FORBIDDEN = "YouTube refused the media request (403); retry later"
    RATE_LIMIT = "YouTube rate limit reached (429); retry later"
    UNAVAILABLE = "YouTube video is unavailable or requires sign-in"
    FORMAT = "No compatible media format was available"
    NETWORK = "Media network request failed; check the connection and retry"


class MediaDownloadError(Exception):
    """Media retrieval or conversion failed; only enum diagnostics are public."""

    def __init__(self, message: str, *, reason: MediaFailure = MediaFailure.UNKNOWN) -> None:
        super().__init__(message)
        self.reason = reason


class MediaDownloader(Protocol):
    """Write a complete MP3 or MP4 at a new target, or raise.

    Implementations must be asynchronous and clean up on failure/cancellation.
    The caller owns the target directory and must serialize writes to each target.
    """

    async def audio(self, url: str, target: Path) -> None: ...
    async def video(self, url: str, target: Path) -> None: ...
