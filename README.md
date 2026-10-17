# Linux USDB Scrapper

A Python + PySide6 desktop application for Linux and Windows, planned in
[Trello](https://trello.com/b/KnffFXKA/usdb-scrapper-linux).

Current status: development foundation and SongEntry domain model. The window launches; search, login,
downloads, and library management are not implemented yet.

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

## Next work

Review the Song Entry model (card 9), then implement the UltraStar TXT in-memory
model (card 10). Investigate USDB authentication in an isolated spike (card 14) before
building the session client. Keep live credentials and session captures out of Git.
