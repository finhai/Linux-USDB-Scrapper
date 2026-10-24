# Versioning and releases

`pyproject.toml` is the version source. Version 1.0.0 is prepared for release;
creating binaries does not tag or publish a release automatically.

Run `uv sync --locked`, `uv run python scripts/check.py`, and `uv build`.
On each native OS, run `uv run python scripts/build_desktop.py`, then
`uv run python scripts/check_package.py`, then `uv run python scripts/package_release.py`.
The Desktop packages workflow performs these steps on Linux and Windows.

Outputs:
- Linux x86-64: `USDB-Scrapper-1.0.0-x86_64.AppImage`.
- Windows x86-64: `USDB-Scrapper-1.0.0-windows-x86_64.zip`; extract the whole archive
  and run `USDB-Scrapper/USDB-Scrapper.exe`. Keep `_internal` and `tools` beside it.
- SHA-256 checksum files accompany the release archives.

Python, Qt, yt-dlp, FFmpeg and ffprobe are included. Linux needs a graphical
session and native keyring service to remember login. AppImage normally uses
FUSE; `--appimage-extract-and-run` is available on systems without FUSE.
Windows packages are unsigned and may trigger the operating system's trust prompt.
FFmpeg archives and appimagetool are pinned and SHA-256 verified; upstream license
files and FFmpeg source/build references are included with the package.

Before publishing: require CI and packaging checks, test real login/download and
UltraStar playback on target machines, review the release PR, then merge into
prod and create the matching immutable `v1.0.0` tag. Attach verified artifacts to
the GitHub release. Later fixes receive a new patch version.
