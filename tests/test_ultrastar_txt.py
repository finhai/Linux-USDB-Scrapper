"""The model preserves song text; interpreting it belongs to the parser."""

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from usdb_scrapper.domain.ultrastar_txt import UltraStarTxt


@pytest.fixture
def song():
    return UltraStarTxt(
        version="2.0.0",
        title=" Don't Stop! ",
        artist="Björk / AC/DC",
        audio="song.mp3",
        bpm=Decimal("123.456789012345678900"),
        video="song.mp4",
        cover="song.jpg",
        note_block=": 0 4 60 Héllo  \r\n- 4\r\n\r\nE\r\n",
    )


def test_genre_can_be_absent_or_explicitly_none(song):
    assert song.genre is None
    assert replace(song, genre=None) == song
    assert replace(song, genre="Rock, Pop").genre == "Rock, Pop"


def test_metadata_is_preserved_without_normalization(song):
    assert song.title == " Don't Stop! "
    assert song.artist == "Björk / AC/DC"
    assert song.bpm.as_tuple() == Decimal("123.456789012345678900").as_tuple()


@pytest.mark.parametrize(
    "body",
    [
        ": 0 4 60 Héllo  \n- 4\nE\n",
        ": 0 4 60 Héllo\r\nE\r\n",
        "P1\r: 0 4 60 a\rP2\r: 0 4 60 b\rE",
        "\t\nE",
        "",
        "not parsed here",
    ],
)
def test_media_replacement_preserves_opaque_body_exactly(song, body):
    original = replace(song, note_block=body)
    updated = replace(original, audio="new.mp3", video="new.mp4", cover="new.jpg")
    assert updated.note_block.encode("utf-8") == body.encode("utf-8")
    assert original.audio == "song.mp3"
    assert (updated.audio, updated.video, updated.cover) == ("new.mp3", "new.mp4", "new.jpg")


def test_snapshot_is_immutable_and_replacement_is_validated(song):
    with pytest.raises(FrozenInstanceError):
        song.audio = "other.mp3"
    with pytest.raises(ValueError, match="bpm"):
        replace(song, bpm=Decimal("0"))


@pytest.mark.parametrize(
    "field", ["version", "title", "artist", "audio", "video", "cover", "genre"]
)
@pytest.mark.parametrize("value", ["", " \t", "first\nsecond", "first\rsecond"])
def test_bad_header_values_are_rejected(song, field, value):
    with pytest.raises(ValueError, match=field):
        replace(song, **{field: value})


@pytest.mark.parametrize(
    "field", ["version", "title", "artist", "audio", "video", "cover", "genre", "note_block"]
)
def test_non_text_is_rejected(song, field):
    with pytest.raises(TypeError, match=field):
        replace(song, **{field: 42})


@pytest.mark.parametrize("field", ["title", "artist", "audio", "video", "note_block"])
def test_required_fields_cannot_be_none(song, field):
    with pytest.raises(TypeError, match=field):
        replace(song, **{field: None})


@pytest.mark.parametrize(
    "bpm",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_invalid_bpm_is_rejected(song, bpm):
    with pytest.raises(ValueError, match="bpm"):
        replace(song, bpm=bpm)


@pytest.mark.parametrize("bpm", [True, 120, 120.5, "120.5", "120,5", None])
def test_bpm_is_not_coerced_or_parsed(song, bpm):
    with pytest.raises(TypeError, match="bpm"):
        replace(song, bpm=bpm)


@pytest.mark.parametrize("version", ["1", "2.0", "v2.0.0", "2.0.0rc1", "-1.0.0", "２.０.０"])
def test_version_shape_is_validated(song, version):
    with pytest.raises(ValueError, match="version"):
        replace(song, version=version)


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0", "2.0.0"])
def test_version_and_bpm_are_not_converted(song, version):
    updated = replace(song, version=version)
    assert updated.version == version
    assert updated.bpm == song.bpm


def test_missing_source_version_and_cover_are_explicit(song):
    updated = replace(song, version=None, cover=None)
    assert updated.version is None
    assert updated.cover is None
    assert updated.note_block == song.note_block
