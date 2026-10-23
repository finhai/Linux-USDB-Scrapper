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


def _write_record(journal: Path, data: dict[str, object]) -> None:
    temporary = journal.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, journal)


def _recover(journal: Path) -> None:
    """Restore interrupted file replacements; never remove the final directory."""
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
        state = data.get("state")
        if state == "replacing":
            names = data["files"]
            if (
                not isinstance(names, list)
                or len(names) != 4
                or len(set(names)) != 4
                or any(
                    not isinstance(n, str) or Path(n).name != n or n in ("", ".", "..")
                    for n in names
                )
            ):
                raise ValueError()
            staging.mkdir(exist_ok=True)
            # Backups remain intact until every old file has been restored, so a
            # second crash during recovery is safe to retry.
            for filename in names:
                original = backup / filename
                if original.is_symlink() or not original.is_file():
                    raise ValueError()
                temporary = staging / (filename + ".restore")
                temporary.unlink(missing_ok=True)
                shutil.copy2(original, temporary)
                os.replace(temporary, destination / filename)
            data["state"] = "aborted"
            _write_record(journal, data)
        elif state is None and backup.exists() and not destination.exists():
            # Recover journals written by the earlier directory-rename prototype.
            backup.rename(destination)
        elif state not in (None, "preparing", "committed", "aborted"):
            raise ValueError()
        if backup.exists():
            shutil.rmtree(backup)
        if staging.exists():
            shutil.rmtree(staging)
        journal.with_suffix(".tmp").unlink(missing_ok=True)
        journal.unlink()
    except (OSError, ValueError, KeyError, TypeError):
        raise BundleStorageError("Library transaction needs manual inspection") from None


def recover_directory(parent: Path) -> int:
    """Recover only app journals; active transactions stay protected by their locks."""
    count = 0
    for journal in parent.glob(".usdb-txn-*.json"):
        name = journal.name[len(".usdb-txn-") : -len(".json")]
        try:
            # Windows can release a terminated process's byte-range lock shortly
            # after its process handle signals completion. Allow a bounded grace
            # period while still skipping a transaction owned by a live process.
            with FileLock(str(parent / f".usdb-lock-{name}"), timeout=0.5, preserve_lock_file=True):
                _recover(journal)
                count += 1
        except Timeout:
            continue
    return count


class BundleStage:
    """Single-song transaction with an OS lock released automatically after a crash.

    Existing files are atomically replaced only after a complete download and
    backup. The final paths stay present. Interrupted groups roll back on restart.
    This is process-crash recovery, not a power-loss durability guarantee.
    """

    def __init__(self, bundle: DownloadBundle):
        paths = [Path(getattr(bundle, kind)) for kind in KINDS]
        if len({path.parent for path in paths}) != 1 or len(set(paths)) != 4:
            raise BundleStorageError("Bundle targets must be distinct files in one directory")
        self.destination = paths[0].parent
        if self.destination.name in ("", ".", "..") or self.destination.is_symlink():
            raise BundleStorageError("Invalid bundle directory")
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(
            str(self.destination.parent / f".usdb-lock-{self.destination.name}"),
            preserve_lock_file=True,
        )
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
                json.dump(
                    {
                        "destination": self.destination.name,
                        "token": token,
                        "state": "preparing",
                        "files": [p.name for p in paths],
                    },
                    stream,
                )
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
            self._backup.mkdir()
            for existing_path in self.destination.iterdir():
                try:
                    os.link(existing_path, self._backup / existing_path.name)
                except OSError:
                    shutil.copy2(existing_path, self._backup / existing_path.name)
            data = json.loads(self._journal.read_text(encoding="utf-8"))
            data["state"] = "replacing"
            _write_record(self._journal, data)
            # Every replace is atomic: readers always see a whole old or new file.
            # TXT goes last; an interrupted group is rolled back during recovery.
            for kind in ("audio", "video", "cover", "txt"):
                path = self.paths[kind]
                os.replace(path, self.destination / path.name)
            data["state"] = "committed"
            _write_record(self._journal, data)
        else:
            self.directory.rename(self.destination)
        self._published = True
        self.discard()

    def discard(self) -> None:
        try:
            if self._journal.exists():
                _recover(self._journal)
        finally:
            self._lock.release()
