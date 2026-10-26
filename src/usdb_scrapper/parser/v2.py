"""Explicit migration to the UltraStar 2.0.0 draft (reviewed 2026-10-20)."""

import re
from dataclasses import replace
from decimal import localcontext
from fractions import Fraction

from usdb_scrapper.parser.export import LocalMedia, TxtExportError, serialize_local_txt
from usdb_scrapper.parser.txt import ParsedTxt


def _number(value: str, *, signed: bool = False) -> Fraction:
    pattern = r"-?[0-9]+(?:[.,][0-9]+)?" if signed else r"[0-9]+(?:[.,][0-9]+)?"
    if not re.fullmatch(pattern, value):
        raise TxtExportError("Invalid timing metadata")
    return Fraction(value.replace(",", "."))


def _milliseconds(value: Fraction, *, signed: bool = False) -> str:
    if value.denominator != 1 or (value < 0 and not signed):
        raise TxtExportError("Timing cannot be represented as exact v2 milliseconds")
    return str(value.numerator)


def migrate_to_v2(parsed: ParsedTxt) -> ParsedTxt:
    """Normalize legacy/v1 timing; v2 input is not converted a second time."""
    source = parsed.song.version
    if source not in (None, "1.0.0", "1.1.0", "2.0.0"):
        raise TxtExportError("Unsupported source version for v2 migration")
    extras = dict(parsed.extra_headers)
    if len(extras) != len(parsed.extra_headers):
        raise TxtExportError("Duplicate extra header")
    if any(key in extras for key in ("RELATIVE", "RESOLUTION")):
        raise TxtExportError("Legacy relative/resolution timing requires separate conversion")
    legacy = source != "2.0.0"
    bpm = parsed.song.bpm
    if legacy:
        with localcontext() as context:
            context.prec = max(28, len(bpm.as_tuple().digits) + 2)
            bpm = bpm * 4
    gap = _number(extras.get("GAP", "0"))
    converted: list[tuple[str, str]] = []
    for key, value in parsed.extra_headers:
        if key == "ENCODING":
            continue  # Output encoding is UTF-8, irrespective of the source label.
        if key in ("GAP", "START", "END", "VIDEOGAP", "PREVIEWSTART", "MEDLEYSTART", "MEDLEYEND"):
            number = _number(value, signed=key == "VIDEOGAP")
            if legacy and key in ("START", "VIDEOGAP", "PREVIEWSTART"):
                number *= 1000
            value = _milliseconds(number, signed=key == "VIDEOGAP")
        if key in ("MEDLEYSTARTBEAT", "MEDLEYENDBEAT"):
            if not legacy:
                raise TxtExportError("Legacy medley beat header in v2 input")
            if not re.fullmatch(r"[0-9]+", value):
                raise TxtExportError("Invalid medley beat")
            key = "MEDLEYSTART" if key == "MEDLEYSTARTBEAT" else "MEDLEYEND"
            if key in extras:
                raise TxtExportError("Conflicting medley headers")
            value = _milliseconds(gap + Fraction(value) * 60000 / Fraction(bpm))
        converted.append((key, value))
    result = replace(
        parsed, song=replace(parsed.song, version="2.0.0", bpm=bpm), extra_headers=tuple(converted)
    )
    # Voice labels are conditional required headers. Do not invent singer names.
    labels = dict(result.extra_headers)
    for line in re.split(r"\r\n|\r|\n", result.song.note_block):
        if line.strip() == "E":
            break
        voice = re.fullmatch(r"P([0-9])\s*", line)
        if voice and (voice[1] == "0" or not labels.get("P" + voice[1], "").strip()):
            raise TxtExportError("Missing required voice label")
    return result


def serialize_v2_txt(parsed: ParsedTxt, media: LocalMedia) -> bytes:
    """Return UTF-8 without BOM, required headers, and exact original note text.

    Validates required metadata and timing conversions, not all musical syntax.
    """
    migrated = migrate_to_v2(parsed)
    output = serialize_local_txt(migrated, media)
    try:
        return output.encode("utf-8", errors="strict")
    except UnicodeError:
        raise TxtExportError("Song contains text that cannot be encoded as UTF-8") from None
