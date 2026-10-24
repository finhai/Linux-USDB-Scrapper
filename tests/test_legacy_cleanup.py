from pathlib import Path

import pytest
from filelock import FileLock

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.normalization.filesystem import normalize_filesystem_name
from usdb_scrapper.storage_manager.legacy import cleanup_legacy
from usdb_scrapper.storage_manager.library import Library


def setup_library(root, complete=True):
    song = SongEntry(
        song_id=32412, artist="Sexyy Red & Bruno Mars", title="Fat Juicy & Wet [EXPLICIT]"
    )
    artist = root / normalize_filesystem_name(song.artist)
    old = artist / f"{normalize_filesystem_name(song.title)}id{song.song_id}"
    old.mkdir(parents=True)
    for ext in ("txt", "mp3", "mp4", "jpg"):
        (old / f"song.{ext}").write_bytes(b"old media")
    if complete:
        bundle = Library(root).bundle(song)
        Path(bundle.txt).parent.mkdir(parents=True)
        for kind in ("txt", "audio", "video", "cover"):
            Path(getattr(bundle, kind)).write_bytes(b"new media")
    return song, old


def test_removes_old_bundle_and_empty_artist_after_success(tmp_path):
    song, old = setup_library(tmp_path)
    assert cleanup_legacy(tmp_path, song)
    assert not old.parent.exists()
    assert Path(Library(tmp_path).bundle(song).txt).read_bytes() == b"new media"


def test_no_replacement_preserves_only_copy(tmp_path):
    song, old = setup_library(tmp_path, complete=False)
    assert not cleanup_legacy(tmp_path, song)
    assert len(list(old.iterdir())) == 4


def test_unrecognized_files_preserved(tmp_path):
    song, old = setup_library(tmp_path)
    (old / "notes.txt").write_text("keep")
    assert not cleanup_legacy(tmp_path, song)
    assert len(list(old.iterdir())) == 5


def test_other_songs_preserved(tmp_path):
    song, old = setup_library(tmp_path)
    other = old.parent / "another-song"
    other.mkdir()
    assert cleanup_legacy(tmp_path, song)
    assert other.is_dir()


def test_active_legacy_download_preserved(tmp_path):
    song, old = setup_library(tmp_path)
    with FileLock(str(old.parent / f".usdb-lock-{old.name}"), preserve_lock_file=True):
        assert not cleanup_legacy(tmp_path, song)
    assert old.exists()


def test_legacy_symlink_preserved(tmp_path):
    song, old = setup_library(tmp_path)
    target = tmp_path / "keep.txt"
    target.write_text("keep")
    (old / "song.txt").unlink()
    try:
        (old / "song.txt").symlink_to(target)
    except OSError:
        pytest.skip("Symlinks unavailable")
    assert not cleanup_legacy(tmp_path, song)
    assert target.read_text() == "keep"


def test_interrupted_cleanup_can_resume(tmp_path):
    song, old = setup_library(tmp_path)
    (old / "song.mp3").unlink()
    assert cleanup_legacy(tmp_path, song)
    assert not old.parent.exists()
