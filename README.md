# Linux USDB Scrapper

A Python + PySide6 desktop application for Linux and Windows, planned in
[Trello](https://trello.com/b/KnffFXKA/usdb-scrapper-linux).

Current branch: desktop shell, domain models, session client, paginated search,
YouTube detail extraction, and a staged search pipeline. Backend APIs are available
in Python; the desktop UI still has no login, search, downloads, or library management.

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

The [session client](docs/session-client.md) passed real-site login and subsequent
request verification. Continue with the remaining authentication/search cards.
Keep credentials and session captures out of Git.
