"""Normalize legacy headers while keeping the body and other headers intact."""

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from usdb_scrapper.domain import UltraStarTxt


class TxtParseError(ValueError):
    """Malformed or insufficient song metadata; messages contain no song content."""


@dataclass(frozen=True)
class ParsedTxt:
    song: UltraStarTxt
    extra_headers: tuple[tuple[str, str], ...]
    video_metadata: tuple[tuple[str, str], ...] = ()
    source_headers: tuple[str, ...] = field(default=(), compare=False, repr=False)


def parse_txt(
    text: str,
    *,
    default_version: str | None = None,
    default_video: str | None = None,
    default_cover: str | None = None,
) -> ParsedTxt:
    """Parse headers; require explicit defaults for missing model-required fields.

    AUDIO wins over MP3. The v=<11-character ID> meta-tag becomes a YouTube
    URL. Other VIDEO values remain literal. Unknown headers are retained for
    later editing/serialization, and the body is never stripped or rewritten.
    """
    if not isinstance(text, str):
        raise TypeError("TXT input must be text")
    if text.startswith("\ufeff"):
        text = text[1:]
    headers: dict[str, str] = {}
    offset = 0
    source_headers: list[str] = []
    for line in text.splitlines(keepends=True):
        if not line.startswith("#"):
            break
        match = re.fullmatch(r"#([A-Za-z][A-Za-z0-9_]*):(.*)", line.rstrip("\r\n"))
        if not match:
            raise TxtParseError("Malformed TXT header")
        key, value = match[1].upper(), match[2].strip()
        if key in headers:
            raise TxtParseError("Duplicate TXT header")
        headers[key] = value
        offset += len(line)
        source_headers.append(line)
    body = text[offset:]
    if not body.strip():
        raise TxtParseError("Missing TXT note block")

    def required(key: str, fallback: str | None = None) -> str:
        value = headers.get(key, fallback)
        if not value or not value.strip():
            raise TxtParseError(f"Missing required {key} metadata")
        return value

    video = required("VIDEO", default_video)
    video_metadata: dict[str, str] = {}
    if video.startswith("v="):
        for part in video.split(","):
            key, separator, value = part.partition("=")
            if (
                not separator
                or not re.fullmatch(r"[a-z][a-z0-9_]*", key)
                or not value
                or key in video_metadata
            ):
                raise TxtParseError("Malformed or duplicate VIDEO meta-tag")
            video_metadata[key] = value
        video_id = video_metadata.pop("v")
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise TxtParseError("Invalid VIDEO meta-tag ID")
        video = "https://www.youtube.com/watch?v=" + video_id
    try:
        song = UltraStarTxt(
            version=headers.get("VERSION", default_version),
            title=required("TITLE"),
            artist=required("ARTIST"),
            audio=required("AUDIO", headers.get("MP3")),
            bpm=Decimal(required("BPM").replace(",", ".")),
            video=video,
            cover=headers.get("COVER", default_cover),
            genre=headers.get("GENRE") or None,
            note_block=body,
        )
    except (ValueError, InvalidOperation):
        raise TxtParseError("Missing or invalid required TXT metadata") from None
    known = {"VERSION", "TITLE", "ARTIST", "AUDIO", "MP3", "BPM", "VIDEO", "COVER", "GENRE"}
    return ParsedTxt(
        song,
        tuple((key, val) for key, val in headers.items() if key not in known),
        tuple(video_metadata.items()),
        tuple(source_headers),
    )
