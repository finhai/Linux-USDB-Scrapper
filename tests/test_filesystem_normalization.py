"""Names remain safe and distinct without consulting the filesystem."""

import re
from pathlib import PurePosixPath, PureWindowsPath

import pytest

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.normalization.filesystem import MAX_COMPONENT_LENGTH, normalize_filesystem_name


@pytest.mark.parametrize(
    "source",
    [
        "AC/DC",
        "B.o.B",
        "BOB",
        "CON",
        "con.txt",
        "NUL",
        "AUX",
        "PRN",
        "COM1",
        "LPT9",
        "COM¹",
        "..",
        "../escape",
        "C:\\Windows\\file",
        "\\\\server\\share",
        'a<>:"/\\|?*b',
        "trailing. ",
        "\x00\x01song",
        "東京",
        "🎵",
        "a" * 10000,
        "Björk",
        "Don't Stop",
    ],
)
def test_portable_bounded_single_component(source):
    name = normalize_filesystem_name(source)
    assert re.fullmatch(r"[a-z0-9]+", name)
    assert len(name.encode("ascii")) <= MAX_COMPONENT_LENGTH
    assert PurePosixPath(name).name == name
    assert PureWindowsPath(name).name == name
    assert not PureWindowsPath(name).is_reserved()
    assert normalize_filesystem_name(source) == name


@pytest.mark.parametrize(
    "left,right",
    [
        ("B.o.B", "BOB"),
        ("AC/DC", "ACDC"),
        ("Artist", "artist"),
        ("Björk", "Bjork"),
        ("a b", "ab"),
        ("東京", "大阪"),
        ("a" * 100 + "b", "a" * 100 + "c"),
        ("Song", "Song "),
        ("!!!", "???"),
    ],
)
def test_lossy_prefix_does_not_collapse_distinct_names(left, right):
    assert normalize_filesystem_name(left).casefold() != normalize_filesystem_name(right).casefold()


def test_canonical_unicode_equivalence_is_deliberate():
    assert normalize_filesystem_name("Björk") == normalize_filesystem_name("Bjo\u0308rk")


def test_fixed_vector_guards_naming_algorithm():
    assert normalize_filesystem_name("abc") == "nabcxba7816bf8f01cfea414140de5dae2223"


def test_preserves_original_metadata():
    song = SongEntry(song_id=1, artist="AC/DC", title="Don't Stop!")
    normalize_filesystem_name(song.artist)
    normalize_filesystem_name(song.title)
    assert (song.artist, song.title) == ("AC/DC", "Don't Stop!")


@pytest.mark.parametrize("value", ["", " ", "\t\r\n", "\u2003"])
def test_blank_input_rejected(value):
    with pytest.raises(ValueError, match="blank"):
        normalize_filesystem_name(value)


@pytest.mark.parametrize("value", [None, 42, b"abc"])
def test_non_string_rejected(value):
    with pytest.raises(TypeError, match="string"):
        normalize_filesystem_name(value)


def test_invalid_unicode_rejected():
    with pytest.raises(ValueError, match="Unicode"):
        normalize_filesystem_name("\ud800")
