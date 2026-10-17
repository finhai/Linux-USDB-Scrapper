"""Contract tests for search results before infrastructure is implemented."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime

import pytest

from usdb_scrapper.domain import SongEntry


def entry(**overrides):
    return SongEntry(**{"song_id": 42, "artist": " AC/DC ", "title": "Dón't Stop!", **overrides})


def test_minimal_result_preserves_semantic_text_and_unknown_metadata():
    song = entry()
    assert (song.song_id, song.artist, song.title) == (42, " AC/DC ", "Dón't Stop!")
    assert song.youtube_url is None
    assert song.golden_notes is None
    assert song.rating is None
    assert song.views is None


def test_complete_result_and_zero_values():
    song = entry(
        youtube_url="https://youtu.be/abcdefghijk",
        date=date(2026, 1, 2),
        genre="Rock",
        year=1980,
        edition="Community",
        golden_notes=False,
        language="English",
        creator="Example",
        rating=0.0,
        views=0,
        last_modified=date(2026, 2, 3),
    )
    assert song.date == date(2026, 1, 2)
    assert song.last_modified == date(2026, 2, 3)
    assert (song.genre, song.year, song.edition) == ("Rock", 1980, "Community")
    assert (song.language, song.creator) == ("English", "Example")
    assert song.golden_notes is False
    assert song.rating == 0.0 and song.views == 0


def test_enrichment_creates_new_snapshot_with_same_identity():
    original = entry()
    enriched = replace(original, youtube_url="https://www.youtube.com/watch?v=abcdefghijk")
    assert enriched.song_id == original.song_id
    assert enriched != original  # Value equality is not identity-based deduplication.
    assert original.youtube_url is None
    with pytest.raises(FrozenInstanceError):
        original.title = "Changed"
    with pytest.raises(ValueError):
        replace(original, song_id=0)


@pytest.mark.parametrize(
    "field,value",
    [
        ("song_id", 0),
        ("song_id", -1),
        ("artist", ""),
        ("title", " \t"),
        ("genre", ""),
        ("edition", " "),
        ("language", ""),
        ("creator", ""),
        ("year", 0),
        ("year", 10000),
        ("views", -1),
        ("rating", -0.1),
        ("rating", float("nan")),
        ("rating", float("inf")),
        ("rating", -float("inf")),
    ],
)
def test_invalid_values_are_rejected(field, value):
    with pytest.raises(ValueError, match=field):
        entry(**{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("song_id", True),
        ("song_id", "42"),
        ("song_id", 1.5),
        ("artist", None),
        ("title", 123),
        ("genre", []),
        ("year", True),
        ("views", 1.5),
        ("views", False),
        ("golden_notes", 1),
        ("rating", True),
        ("rating", "4.5"),
        ("date", "2026-01-02"),
        ("last_modified", datetime(2026, 1, 2)),
        ("youtube_url", 123),
    ],
)
def test_values_are_not_silently_coerced(field, value):
    with pytest.raises(TypeError, match=field):
        entry(**{field: value})


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abcdefghijk&t=30",
        "http://youtube.com/watch?v=abcdefghijk",
        "https://m.youtube.com/watch?v=abcdefghijk",
        "https://youtu.be/abcdefghijk",
        "https://www.youtube.com/shorts/abcdefghijk",
    ],
)
def test_youtube_links_are_preserved_without_resolving(url):
    assert entry(youtube_url=url).youtube_url == url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "abcdefghijk",
        "ftp://youtu.be/abcdefghijk",
        "https://example.com/video",
        "https://youtube.com.evil.example/watch?v=abcdefghijk",
        "https://youtube.com@evil.example/video",
        "https://user@youtube.com/video",
        "https://youtu.be",
        "https://youtu.be/",
        "https://youtu.be:123/video",
        "https://youtu.be:invalid/video",
        "https://[invalid/video",
        " https://youtu.be/video",
        "https://youtu.be/vid\neo",
    ],
)
def test_malformed_or_non_youtube_links_are_rejected(url):
    with pytest.raises(ValueError, match="youtube_url"):
        entry(youtube_url=url)
