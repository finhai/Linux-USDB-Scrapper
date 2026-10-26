"""Persistent per-user coordination state; never stored in the song library."""

import hashlib
import os
from pathlib import Path


def bundle_lock_path(destination: Path) -> Path:
    # Resolve aliases so two app instances targeting the same folder share a lock.
    identity_path = os.path.normcase(str(destination.resolve()))
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    folder = base / "usdb-scrapper" / "locks"
    if folder.is_symlink():
        raise ValueError("Application lock directory must not be a symlink")
    folder.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256(identity_path.encode("utf-8")).hexdigest()
    return folder / identity
