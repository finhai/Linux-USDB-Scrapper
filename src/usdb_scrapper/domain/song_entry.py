"""Validated search-result data, independent of retrieval and presentation."""

import math
from dataclasses import dataclass
from datetime import date as Date
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True, kw_only=True)
class SongEntry:
    """An immutable snapshot; use song_id as the key when deduplicating.

    Missing metadata and an unresolved/absent YouTube link are represented by
    None. Text is preserved verbatim. Extraction, coercion, normalization, and
    checking whether a video is playable belong to other components.
    """

    song_id: int
    artist: str
    title: str
    youtube_url: str | None = None
    date: Date | None = None
    genre: str | None = None
    year: int | None = None
    edition: str | None = None
    golden_notes: bool | None = None
    language: str | None = None
    creator: str | None = None
    rating: float | None = None
    views: int | None = None
    last_modified: Date | None = None

    def __post_init__(self) -> None:
        _integer("song_id", self.song_id, minimum=1)
        _text("artist", self.artist)
        _text("title", self.title)
        for name in ("genre", "edition", "language", "creator"):
            value = getattr(self, name)
            if value is not None:
                _text(name, value)
        if self.year is not None:
            _integer("year", self.year, minimum=1)
            if self.year > 9999:
                raise ValueError("year must be at most 9999")
        if self.views is not None:
            _integer("views", self.views, minimum=0)
        if self.golden_notes is not None and type(self.golden_notes) is not bool:
            raise TypeError("golden_notes must be a bool or None")
        for name in ("date", "last_modified"):
            value = getattr(self, name)
            if value is not None and type(value) is not Date:
                raise TypeError(f"{name} must be a date or None")
        if self.rating is not None:
            if type(self.rating) not in (int, float):
                raise TypeError("rating must be a number or None")
            if not math.isfinite(self.rating) or self.rating < 0:
                raise ValueError("rating must be finite and non-negative")
        if self.youtube_url is not None:
            _youtube_url(self.youtube_url)


def _integer(name: str, value: int, *, minimum: int) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be an int")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def _text(name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be blank")


def _youtube_url(value: str) -> None:
    _text("youtube_url", value)
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("youtube_url must not contain whitespace or control characters")
    try:
        parts = urlsplit(value)
        valid = (
            parts.scheme in ("http", "https")
            and parts.hostname in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be")
            and parts.username is None
            and parts.password is None
            and parts.port is None
            and parts.path not in ("", "/")
        )
    except ValueError as exc:
        raise ValueError("youtube_url must be a valid YouTube URL") from exc
    if not valid:
        raise ValueError("youtube_url must be an HTTP(S) YouTube URL with a path")
