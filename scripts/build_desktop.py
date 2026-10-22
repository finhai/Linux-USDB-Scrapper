"""Build a native one-folder desktop package on the current platform."""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "USDB-Scrapper",
        "--specpath",
        str(root / "build"),
        "--collect-all",
        "yt_dlp",
        "--collect-all",
        "yt_dlp_ejs",
        "--copy-metadata",
        "usdb-scrapper-linux",
        "--hidden-import",
        "keyring.backends.SecretService",
        "--hidden-import",
        "keyring.backends.Windows",
        str(root / "src/usdb_scrapper/__main__.py"),
    ],
    cwd=root,
    check=True,
)
