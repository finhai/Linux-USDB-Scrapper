"""Retire exact pre-readable-name bundles after a successful replacement."""

from pathlib import Path

from filelock import FileLock, Timeout

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.normalization.filesystem import normalize_filesystem_name
from usdb_scrapper.storage_manager.library import Library
from usdb_scrapper.storage_manager.locks import bundle_lock_path


def cleanup_legacy(root: Path, song: SongEntry) -> bool:
    """Remove only known legacy files; never sweep arbitrary library directories.

    Old application versions must not be started during migration. An already
    active legacy transaction is skipped. Partial cleanup can be retried safely.
    """
    root = root.resolve()
    current = Library(root).bundle(song)
    current_paths = [Path(getattr(current, kind)) for kind in ("txt", "audio", "video", "cover")]
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size == 0 for p in current_paths):
        return False
    artist = root / normalize_filesystem_name(song.artist)
    old = artist / f"{normalize_filesystem_name(song.title)}id{song.song_id}"
    if artist.is_symlink() or old.is_symlink() or not artist.is_dir():
        return False
    lock_path = artist / f".usdb-lock-{old.name}"
    journal = artist / f".usdb-txn-{old.name}.json"
    if lock_path.is_symlink() or journal.exists():
        return False
    allowed = {f"song.{ext}" for ext in ("txt", "mp3", "mp4", "jpg")}
    try:
        current_dir = Path(current.txt).parent
        current_lock = bundle_lock_path(current_dir)
        with FileLock(str(current_lock), timeout=0, preserve_lock_file=True):
            return _remove_legacy(artist, old, lock_path, journal, allowed)
    except Timeout:
        return False


def _remove_legacy(
    artist: Path, old: Path, lock_path: Path, journal: Path, allowed: set[str]
) -> bool:
    try:
        with FileLock(str(lock_path), timeout=0, preserve_lock_file=True):
            if journal.exists():
                return False
            if old.exists():
                if not old.is_dir():
                    return False
                files = list(old.iterdir())
                if any(p.name not in allowed or p.is_symlink() or not p.is_file() for p in files):
                    return False
                for path in files:
                    path.unlink()
                old.rmdir()
        # This lock belongs to the retired layout, not to ongoing new downloads.
        lock_path.unlink(missing_ok=True)
        if not any(artist.iterdir()):
            artist.rmdir()
        return True
    except Timeout:
        return False
