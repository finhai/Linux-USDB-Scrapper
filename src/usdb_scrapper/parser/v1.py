"""AUDIO-only export for UltraStar Deluxe's released 1.x parser."""

from dataclasses import replace

from usdb_scrapper.parser.export import LocalMedia, TxtExportError, serialize_local_txt
from usdb_scrapper.parser.txt import ParsedTxt


def serialize_v1_txt(parsed: ParsedTxt, media: LocalMedia) -> bytes:
    """Keep legacy/v1 timing and notes; never relabel draft-v2 timing as v1."""
    if parsed.song.version not in (None, "0.3.0", "1.0.0", "1.1.0"):
        raise TxtExportError("Unsupported source version for player-compatible export")
    extras = dict(parsed.extra_headers)
    if any(key in extras for key in ("RELATIVE", "RESOLUTION", "NOTESGAP")):
        raise TxtExportError("Legacy timing extensions require separate conversion")
    headers = []
    for key, value in parsed.extra_headers:
        if key == "ENCODING":
            continue
        renamed = {"DUETSINGERP1": "P1", "DUETSINGERP2": "P2"}.get(key, key)
        if renamed != key and renamed in extras:
            raise TxtExportError("Conflicting singer labels")
        headers.append((renamed, value))
    normalized = replace(
        parsed, song=replace(parsed.song, version="1.0.0"), extra_headers=tuple(headers)
    )
    try:
        return serialize_local_txt(normalized, media).encode("utf-8", errors="strict")
    except UnicodeError:
        raise TxtExportError("Song contains text that cannot be encoded as UTF-8") from None
