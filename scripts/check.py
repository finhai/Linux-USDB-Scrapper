"""Run the same quality gates locally and in CI: uv run python scripts/check.py."""

import subprocess
import sys

for args in (
    ["ruff", "format", "--check", "."],
    ["ruff", "check", "."],
    ["mypy"],
    ["pytest"],
):
    subprocess.run([sys.executable, "-m", *args], check=True)
