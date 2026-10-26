import codecs
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction

import pytest

from usdb_scrapper.parser import (
    LocalMedia,
    TxtExportError,
    migrate_to_v2,
    parse_txt,
    serialize_v2_txt,
)

TEXT = "#TITLE:Café\n#ARTIST:Björk\n#MP3:old.mp3\n#BPM:120\n#VIDEO:v=abcdefghijk\n"
BODY = ": 0 4 2  héllo  \r\n- 4\r\nE\r\n"
MEDIA = LocalMedia(audio="song.flac", video="video.mp4", cover="cover.jpg")


def test_required_fields_encoding_and_exact_note_preservation():
    source = parse_txt(TEXT + BODY)
    data = serialize_v2_txt(source, MEDIA)
    assert not data.startswith(codecs.BOM_UTF8)
    text = data.decode("utf-8")
    headers = dict(line[1:].split(":", 1) for line in text.splitlines() if line.startswith("#"))
    assert {"VERSION", "TITLE", "ARTIST", "BPM", "AUDIO"} <= headers.keys()
    assert headers["VERSION"] == "2.0.0"
    assert headers["BPM"] == "480"
    assert "MP3" not in headers
    assert data.endswith(BODY.encode("utf-8"))
    assert parse_txt(text).song.title == "Café"
    assert source.song.version is None and source.song.bpm == Decimal("120")


def test_explicit_time_conversion_preserves_physical_time():
    source = parse_txt(
        TEXT + "#GAP:1250\n#START:2.5\n#END:4000\n#VIDEOGAP:-0.25\n"
        "#PREVIEWSTART:3.25\n#MEDLEYSTARTBEAT:8\n#MEDLEYENDBEAT:16\n" + BODY
    )
    result = migrate_to_v2(source)
    assert dict(result.extra_headers) == {
        "GAP": "1250",
        "START": "2500",
        "END": "4000",
        "VIDEOGAP": "-250",
        "PREVIEWSTART": "3250",
        "MEDLEYSTART": "2250",
        "MEDLEYEND": "3250",
    }
    assert Fraction(8 * 60000, 1) / (Fraction(source.song.bpm) * 4) == Fraction(
        8 * 60000, 1
    ) / Fraction(result.song.bpm)
    assert migrate_to_v2(result) == result


@pytest.mark.parametrize(
    "header",
    [
        "#GAP:0.5",
        "#START:0.0001",
        "#RELATIVE:YES",
        "#RESOLUTION:4",
        "#MEDLEYSTARTBEAT:1\n#MEDLEYSTART:100",
    ],
)
def test_no_silent_rounding_or_ambiguous_conversion(header):
    with pytest.raises(TxtExportError):
        serialize_v2_txt(parse_txt(TEXT + header + "\n" + BODY), MEDIA)


def test_nonrepresentable_medley_time_rejected():
    with pytest.raises(TxtExportError):
        migrate_to_v2(parse_txt(TEXT.replace("120", "123") + "#MEDLEYSTARTBEAT:1\n" + BODY))


def test_duet_requires_voice_names():
    with pytest.raises(TxtExportError):
        serialize_v2_txt(parse_txt(TEXT + "P1\n" + BODY), MEDIA)
    assert b"#P1:Lead" in serialize_v2_txt(parse_txt(TEXT + "#P1:Lead\nP1\n" + BODY), MEDIA)


def test_unsupported_version_and_invalid_unicode_fail():
    source = parse_txt(TEXT + BODY)
    with pytest.raises(TxtExportError):
        migrate_to_v2(replace(source, song=replace(source.song, version="3.0.0")))
    with pytest.raises(TxtExportError):
        serialize_v2_txt(replace(source, song=replace(source.song, title="\ud800")), MEDIA)
