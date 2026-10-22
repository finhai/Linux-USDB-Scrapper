"""Journaled complete-directory publication with bounded-memory comparison."""

import json
import os
import re
import shutil
import uuid
from pathlib import Path

from filelock import FileLock, Timeout

from usdb_scrapper.domain.download_item import DownloadBundle

KINDS = ("txt", "audio", "video", "cover")


class BundleStorageError(ValueError):
    """Sanitized staging or finalization failure."""


def identical(first: Path, second: Path) -> bool:
    if first.is_symlink() or second.is_symlink() or not first.is_file() or not second.is_file():
        return False
    if first.stat().st_size != second.stat().st_size:
        return False
    with first.open("rb") as a, second.open("rb") as b:
        while chunk := a.read(1024 * 1024):
            if chunk != b.read(len(chunk)):
                return False
    return True


def _recover(journal: Path) -> None:
    """Caller holds the target lock. Restore old directory if publication stopped."""
    try:
        data = json.loads(journal.read_text(encoding="utf-8"))
        name, token = data["destination"], data["token"]
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name in ("", ".", "..")
            or not isinstance(token, str)
            or not re.fullmatch(r"[a-f0-9]{32}", token)
            or journal.name != f".usdb-txn-{name}.json"
        ):
            raise ValueError()
        destination = journal.parent / name
        staging = journal.parent / f".usdb-partial-{token}"
        backup = journal.parent / f".usdb-backup-{token}"
        if any(path.is_symlink() for path in (journal, destination, staging, backup)):
            raise ValueError()
        if backup.exists():
            if not destination.exists():
                backup.rename(destination)
            else:
                shutil.rmtree(backup)
        if staging.exists():
            shutil.rmtree(staging)
        journal.unlink()
    except (OSError, ValueError, KeyError, TypeError):
        raise BundleStorageError("Library transaction needs manual inspection") from None


def recover_directory(parent: Path) -> int:
    """Recover only app journals; active transactions stay protected by their locks."""
    count = 0
    for journal in parent.glob(".usdb-txn-*.json"):
        name = journal.name[len(".usdb-txn-") : -len(".json")]
        try:
            with FileLock(str(parent / f".usdb-lock-{name}"), timeout=0):
                _recover(journal)
                count += 1
        except Timeout:
            continue
    return count


class BundleStage:
    """Single-song transaction with an OS lock released automatically after a crash.

    Replacement uses old->backup then staged->final directory renames. There is
    a brief absent-path interval, never a directory of partially downloaded files.
    Journals restore an interrupted replacement on restart. This is process-crash
    recovery, not a filesystem/power-loss durability guarantee.
    """

    def __init__(self, bundle: DownloadBundle):
        paths = [Path(getattr(bundle, kind)) for kind in KINDS]
        if len({path.parent for path in paths}) != 1 or len(set(paths)) != 4:
            raise BundleStorageError("Bundle targets must be distinct files in one directory")
        self.destination = paths[0].parent
        if self.destination.name in ("", ".", "..") or self.destination.is_symlink():
            raise BundleStorageError("Invalid bundle directory")
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.destination.parent / f".usdb-lock-{self.destination.name}"))
        try:
            self._lock.acquire(timeout=0)
        except Timeout:
            raise BundleStorageError("Another download owns this song directory") from None
        self._journal = self.destination.parent / f".usdb-txn-{self.destination.name}.json"
        self._published = False
        try:
            if self._journal.exists():
                _recover(self._journal)
            token = uuid.uuid4().hex
            self.directory = self.destination.parent / f".usdb-partial-{token}"
            self._backup = self.destination.parent / f".usdb-backup-{token}"
            with self._journal.open("x", encoding="utf-8") as stream:
                json.dump({"destination": self.destination.name, "token": token}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            self.directory.mkdir()
            self.paths = {
                kind: self.directory / path.name for kind, path in zip(KINDS, paths, strict=True)
            }
        except Exception:
            self._lock.release()
            raise

    def verify(self) -> None:
        for path in self.paths.values():
            if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
                raise BundleStorageError("Bundle is missing a nonempty regular file")
        if set(self.directory.iterdir()) != set(self.paths.values()):
            raise BundleStorageError("Unexpected files in bundle staging directory")

    def publish(self) -> None:
        self.verify()
        if self.destination.is_symlink():
            raise BundleStorageError("Invalid bundle destination")
        if self.destination.exists():
            if not self.destination.is_dir():
                raise BundleStorageError("Bundle destination is not a directory")
            existing = set(path.name for path in self.destination.iterdir())
            expected = {path.name for path in self.paths.values()}
            if existing != expected:
                raise BundleStorageError("Existing directory has unexpected files; preserve it")
            if any(path.is_symlink() or not path.is_file() for path in self.destination.iterdir()):
                raise BundleStorageError("Existing bundle contains unsupported files")
            if all(identical(path, self.destination / path.name) for path in self.paths.values()):
                self.discard()
                self._published = True
                return
            self.destination.rename(self._backup)
        try:
            self.directory.rename(self.destination)
        except OSError:
            if self._backup.exists() and not self.destination.exists():
                self._backup.rename(self.destination)
            raise BundleStorageError("Cannot publish completed bundle") from None
        self._published = True
        self.discard()

    def discard(self) -> None:
        try:
            if self._journal.exists():
                _recover(self._journal)
        finally:
            self._lock.release()
