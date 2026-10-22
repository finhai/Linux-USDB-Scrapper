"""Normalized UltraStar metadata with an opaque, unchanged song body."""

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class UltraStarTxt:
    """App-required metadata, without file parsing or version conversion.

    The parser supplies normalized values, including a Decimal BPM. The note
    block remains exactly as supplied: no splitting, stripping, or validation
    of note syntax. Missing source version/cover metadata is represented by None.
    Media references are text, not filesystem operations.
    """

    version: str | None = None
    title: str
    artist: str
    audio: str
    bpm: Decimal
    video: str
    cover: str | None = None
    note_block: str
    genre: str | None = None

    def __post_init__(self) -> None:
        for name in ("title", "artist", "audio", "video"):
            _header_value(name, getattr(self, name))
        if self.version is not None:
            _header_value("version", self.version)
            if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", self.version) is None:
                raise ValueError("version must be a numeric major.minor.patch triplet")
        if self.cover is not None:
            _header_value("cover", self.cover)
        if not isinstance(self.bpm, Decimal):
            raise TypeError("bpm must be a Decimal")
        if not self.bpm.is_finite() or self.bpm <= 0:
            raise ValueError("bpm must be finite and positive")
        if not isinstance(self.note_block, str):
            raise TypeError("note_block must be a string")
        if self.genre is not None:
            _header_value("genre", self.genre)


def _header_value(name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be blank")
    if "\r" in value or "\n" in value:
        raise ValueError(f"{name} must be a single-line header value")
