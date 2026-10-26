"""Smoke-test packaged entry points without relying on a Python executable on PATH."""

import os
import subprocess
from pathlib import Path

name = "USDB-Scrapper.exe" if os.name == "nt" else "USDB-Scrapper"
executable = Path("dist/USDB-Scrapper", name).resolve()
environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
if os.name == "posix":
    environment["PATH"] = ""
for arguments in (["--version"], ["--media-worker", "--version"], ["--smoke-test"]):
    subprocess.run([str(executable), *arguments], check=True, timeout=60, env=environment)
