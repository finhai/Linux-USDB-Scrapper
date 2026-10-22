# Linux USDB Scrapper

A Python + PySide6 desktop application for Linux and Windows, planned in
[Trello](https://trello.com/b/KnffFXKA/usdb-scrapper-linux).

The desktop now provides deferred login, paginated search, a download queue with
cancel/retry, and persistent settings. Downloads create TXT/MP3/MP4/JPG bundles
under normalized Artist/Song directories, with restart recovery. Credentials use
the native OS keyring when available.

See [install and first run](docs/install.md) for launch commands and the remaining
release-validation limits. This is a development build, not yet a verified
cross-platform release.

## Start developing

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/)
(version 0.13.1 used in CI), then from this checkout run:

```sh
uv sync --locked
```

This installs the pinned Python and locked development/runtime dependencies.
Run the desktop shell with `uv run usdb-scrapper` and check the installed version
with `uv run usdb-scrapper --version`.
Linux needs a working desktop session and Qt system libraries; minimal systems
may need libEGL, libGL, and xkbcommon. CI runs a headless Qt smoke test.

```sh
uv run python scripts/check.py
uv build
```

The first command runs formatting, lint, strict type checks, and tests.
The second builds a Python wheel and source distribution, not a standalone desktop installer.

See [contributing](CONTRIBUTING.md), [architecture](docs/architecture.md),
[release workflow](docs/releases.md), and the [Trello snapshot](docs/backlog.md).

## Validation status

The real-site login, pagination, TXT retrieval and draft-v2 round trip have been
verified. A real four-file bundle and offline desktop workflow now pass too.
Clean-platform packaging and UltraStar playback acceptance remain open.
