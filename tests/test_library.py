from dataclasses import replace
from pathlib import Path

import pytest

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.storage_manager.library import Library


def test_artist_layout_identity_and_root(tmp_path):
    song = SongEntry(song_id=1, artist="AC/DC", title="Song One")
    library = Library(tmp_path)
    first = library.bundle(song)
    second = library.bundle(replace(song, song_id=2, title="Song Two"))
    assert first.txt.parent.parent == second.txt.parent.parent
    assert first.txt.parent != second.txt.parent
    assert library.bundle(replace(song, artist="ACDC")).txt.parent.parent != first.txt.parent.parent
    assert song.artist == "AC/DC"
    assert first.txt.parent.parent.name.isalnum()
    assert Library(tmp_path / "new").bundle(song).txt.is_relative_to(tmp_path / "new")


def test_artist_symlink_escape_rejected(tmp_path):
    library = Library(tmp_path / "library")
    song = SongEntry(song_id=1, artist="Artist", title="Song")
    artist = Path(library.bundle(song).txt).parent.parent
    artist.parent.mkdir()
    try:
        artist.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks unavailable")
    with pytest.raises(ValueError, match="escapes"):
        library.bundle(song)
