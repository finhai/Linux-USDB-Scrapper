"""Serialize local media references without modifying note data."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from usdb_scrapper.parser.txt import ParsedTxt


class TxtExportError(ValueError):
    """The song cannot be exported without invalid or remote references."""


@dataclass(frozen=True, kw_only=True)
class LocalMedia:
    audio: str
    video: str
    cover: str

    def __post_init__(self) -> None:
        for value in (self.audio, self.video, self.cover):
            if (
                not isinstance(value, str)
                or not value.strip()
                or value in (".", "..")
                or value != value.strip()
                or any(c in value for c in '/\\:<>"|?*')
                or any(ord(c) < 32 or ord(c) == 127 for c in value)
                or value.endswith(".")
                or "=" in value
            ):
                raise TxtExportError("Media references must be plain local filenames")


def serialize_local_txt(parsed: ParsedTxt, media: LocalMedia) -> str:
    """Return TXT with local AUDIO/VIDEO/COVER and an unchanged note block.

    Caller supplies filenames of completed downloads. No filesystem access or
    existence checks occur here. Auxiliary VIDEO download directives are omitted.
    Refuse output containing YouTube hostnames, meta-tags or the known source ID.
    """
    song = parsed.song
    fields = [
        ("TITLE", song.title),
        ("ARTIST", song.artist),
        ("AUDIO", media.audio),
        ("BPM", format(song.bpm, "f")),
        ("VIDEO", media.video),
        ("COVER", media.cover),
    ]
    if song.version is not None:
        fields.insert(0, ("VERSION", song.version))
    if song.genre is not None:
        fields.append(("GENRE", song.genre))
    known = {key for key, _ in fields} | {"VERSION", "GENRE", "MP3"}
    for key, value in parsed.extra_headers:
        if (
            not re.fullmatch(r"[A-Z][A-Z0-9_]*", key)
            or key in known
            or any(c in value for c in "\r\n\x00")
        ):
            raise TxtExportError("Invalid or duplicate extra header")
        known.add(key)
        fields.append((key, value))
    output = _render_headers(parsed, fields) + song.note_block
    if re.search(r"youtube(?:-nocookie)?\.com|youtu\.be|(?:^|[\s:,])v=", output, re.I):
        raise TxtExportError("YouTube reference remains in preserved song content")
    # Track source IDs even if repeated without a URL in another header or lyrics.
    ids = re.findall(r"(?:[?&]v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})", song.video)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", song.video):
        ids.append(song.video)
    if any(video_id in output for video_id in ids):
        raise TxtExportError("Source video ID remains in preserved song content")
    return output


def _render_headers(parsed: ParsedTxt, fields: list[tuple[str, str]]) -> str:
    """Reuse unchanged original lines; rewrite changed fields at their old position."""
    pending = dict(fields)
    lines: list[str] = []
    seen: set[str] = set()
    # A new version declaration belongs first; an existing one keeps its position.
    if "VERSION" in pending and not any(
        line.upper().startswith("#VERSION:") for line in parsed.source_headers
    ):
        lines.append("#VERSION:" + pending.pop("VERSION") + "\n")
    for original in parsed.source_headers:
        match = re.fullmatch(r"#([A-Za-z][A-Za-z0-9_]*):([^\r\n]*)(\r\n|\r|\n)?", original)
        if not match:
            raise TxtExportError("Invalid retained source header")
        source_key = match[1].upper()
        if source_key in seen:
            raise TxtExportError("Duplicate retained source header")
        seen.add(source_key)
        key = "AUDIO" if source_key == "MP3" else source_key
        if key not in pending:
            continue
        value = pending.pop(key)
        ending = match[3] or "\n"
        unchanged = match[2].strip() == value
        if source_key == key == "BPM" and parsed.song.version != "2.0.0":
            try:
                unchanged = Decimal(match[2].strip().replace(",", ".")) == Decimal(value)
            except InvalidOperation:
                unchanged = False
        if source_key == key and unchanged and match[3]:
            lines.append(original)
        else:
            lines.append(f"#{key}:{value}{ending}")
    lines.extend(f"#{key}:{value}\n" for key, value in pending.items())
    return "".join(lines)
