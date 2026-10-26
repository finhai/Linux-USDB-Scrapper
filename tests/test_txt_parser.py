from decimal import Decimal

import pytest

from usdb_scrapper.parser import TxtParseError, parse_txt

HEADER = (
    "#VERSION:1.0.0\n#TITLE:Café\n#ARTIST:Example\n#MP3:song.mp3\n"
    "#BPM:120,5\n#VIDEO:v=xFrGuyw1V8s\n#COVER:cover.jpg\n"
)
BODY = ": 0 4 2  word  \r\n* 4 2 3 é\r\n- 8\r\nE\r\n"


def test_legacy_normalization_preserves_body():
    parsed = parse_txt(HEADER + "#GAP:1234\n" + BODY)
    assert parsed.song.audio == "song.mp3"
    assert parsed.song.video == "https://www.youtube.com/watch?v=xFrGuyw1V8s"
    assert parsed.song.bpm == Decimal("120.5")
    assert parsed.song.note_block == BODY
    assert parsed.extra_headers == (("GAP", "1234"),)


def test_modern_and_legacy_produce_same_model():
    modern = HEADER.replace("#MP3:", "#AUDIO:").replace(
        "v=xFrGuyw1V8s", "https://www.youtube.com/watch?v=xFrGuyw1V8s"
    )
    assert parse_txt(modern + BODY) == parse_txt(HEADER + BODY)
    literal = parse_txt(
        modern.replace("https://www.youtube.com/watch?v=xFrGuyw1V8s", "video.mp4") + BODY
    )
    assert literal.song.video == "video.mp4"


def test_audio_wins_and_unknown_metadata_is_preserved():
    parsed = parse_txt(HEADER + "#AUDIO:new.flac\n#VIDEOGAP:1.5\n" + BODY)
    assert parsed.song.audio == "new.flac"
    assert parsed.extra_headers == (("VIDEOGAP", "1.5"),)


def test_missing_version_is_preserved_and_default_is_opt_in():
    text = HEADER.replace("#VERSION:1.0.0\n", "") + BODY
    assert parse_txt(text).song.version is None
    assert parse_txt(text, default_version="1.0.0").song.version == "1.0.0"


@pytest.mark.parametrize(
    "text",
    [
        HEADER,
        HEADER + "#TITLE:duplicate\n" + BODY,
        HEADER.replace("120,5", "NaN") + BODY,
        HEADER.replace("120,5", "-2") + BODY,
        HEADER.replace("v=xFrGuyw1V8s", "v=bad") + BODY,
        HEADER.replace("#TITLE:Café", "#TITLE") + BODY,
    ],
)
def test_reject_invalid_metadata(text):
    with pytest.raises(TxtParseError):
        parse_txt(text)


def test_bom_and_crlf_headers():
    assert parse_txt("\ufeff" + HEADER.replace("\n", "\r\n") + BODY).song.note_block == BODY


def test_observed_legacy_file_without_version_or_cover():
    text = HEADER.replace("#VERSION:1.0.0\n", "").replace("#COVER:cover.jpg\n", "") + BODY
    legacy = parse_txt(text)
    modern = parse_txt(
        text.replace("#MP3:", "#AUDIO:").replace(
            "#VIDEO:v=xFrGuyw1V8s", "#VIDEO:https://www.youtube.com/watch?v=xFrGuyw1V8s"
        )
    )
    assert legacy == modern
    assert legacy.song.version is None
    assert legacy.song.cover is None
    assert legacy.song.note_block == BODY


def test_compound_video_metadata_preserved_outside_song_model():
    text = HEADER.replace("#VERSION:1.0.0\n", "").replace("#COVER:cover.jpg\n", "")
    text = text.replace(
        "v=xFrGuyw1V8s", "v=xFrGuyw1V8s,co=https://example.org/c.jpg,bg=background.jpg"
    )
    parsed = parse_txt(text + BODY)
    assert parsed.song.video == "https://www.youtube.com/watch?v=xFrGuyw1V8s"
    assert parsed.song.cover is None
    assert parsed.song.version is None
    assert parsed.song.note_block == BODY
    assert parsed.video_metadata == (("co", "https://example.org/c.jpg"), ("bg", "background.jpg"))


@pytest.mark.parametrize("suffix", [",", ",co=", ",co=a,co=b", ",v=abcdefghijk", ",broken"])
def test_bad_compound_meta_tags_fail(suffix):
    with pytest.raises(TxtParseError):
        parse_txt(HEADER.replace("v=xFrGuyw1V8s", "v=xFrGuyw1V8s" + suffix) + BODY)


def test_unknown_meta_value_with_equals_is_not_discarded():
    parsed = parse_txt(
        HEADER.replace("v=xFrGuyw1V8s", "v=xFrGuyw1V8s,custom=https://example.org/?x=y") + BODY
    )
    assert parsed.video_metadata == (("custom", "https://example.org/?x=y"),)
