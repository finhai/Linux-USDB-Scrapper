"""Normalize legacy headers while keeping the body and other headers intact."""

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from usdb_scrapper.domain import UltraStarTxt
from usdb_scrapper.usdb_client.details import youtube_url


class TxtParseError(ValueError):
    """Malformed or insufficient song metadata; messages contain no song content."""


@dataclass(frozen=True)
class ParsedTxt:
    song: UltraStarTxt
    extra_headers: tuple[tuple[str, str], ...]
    video_metadata: tuple[tuple[str, str], ...] = ()
    audio_source: str | None = None
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
    audio_source = None
    if re.match(r"[a-z][a-z0-9_-]*=", video):
        for part in video.split(","):
            key, separator, value = part.partition("=")
            if (
                not separator
                or not re.fullmatch(r"[a-z][a-z0-9_-]*", key)
                or not value
                or key in video_metadata
            ):
                raise TxtParseError("Malformed or duplicate VIDEO meta-tag")
            video_metadata[key] = value

        def resource(value: str) -> str:
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
                return "https://www.youtube.com/watch?v=" + value
            canonical = youtube_url(value)
            if canonical is None:
                raise TxtParseError("Unsupported VIDEO meta-tag resource")
            return canonical

        audio_value = video_metadata.get("a")
        video_value = video_metadata.pop("v", None)
        if audio_value is not None:
            audio_source = resource(audio_value)
        if video_value is None and audio_source is None:
            raise TxtParseError("Missing audio/video resource in VIDEO meta-tag")
        # Audio-only YouTube sources can still provide their own visual stream.
        if video_value is not None:
            video = resource(video_value)
        else:
            assert audio_source is not None
            video = audio_source
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
        source_headers=tuple(source_headers),
        audio_source=audio_source,
    )
