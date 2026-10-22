# Architecture and conventions

Decision: Python + PySide6, as recorded on Trello card 2. A src-layout package
keeps imports tied to the installed project. uv owns Python and dependencies;
pytest, Ruff, and mypy provide the initial quality gates.

Each concern has a sibling package under src/usdb_scrapper:

- domain: pure models and validation, no Qt/network/filesystem imports.
- normalization: independent search and filesystem normalization subpackages.
- usdb_client: authentication, HTTP, page parsing, and raw TXT retrieval.
- parser: UltraStar TXT parsing and serialization; preserve note blocks.
- download_manager: queue, lifecycle, progress, and a replaceable media adapter.
- storage_manager: local paths, staging, and atomic finalization.
- credential_manager: native secure storage, with session-only fallback.
- controllers: application orchestration and translation to view-facing state.
- frontend: Qt views; backend operations go through controllers.

These packages are implemented. The entry point wires the Qt window and application
controller; the controller composes authentication, search, storage and download
services on a dedicated asyncio worker thread. Import public APIs, never another component's private modules.
Network and download work must not block the GUI thread; dispatch through workers
and deliver state changes to the GUI thread via Qt signals.

## Errors and logging

Use standard-library logging with module loggers (`logging.getLogger(__name__)`).
Libraries do not configure handlers; the application entry point will configure
them once logging is introduced. INFO covers lifecycle, WARNING recoverable
failures, ERROR failed operations; DEBUG is opt-in diagnostics.

Raise typed exceptions at service boundaries (authentication, transport, parse,
storage); preserve causes with `raise ... from exc`. Controllers catch expected
failures and produce user-facing states. Unexpected failures are logged once at
the orchestration boundary and shown as a generic failure with a retry path.
Do not swallow exceptions or represent failure as empty success results.
Never log passwords, cookies, authorization headers, or raw authenticated pages.

## Unresolved research

The spike verified form POST and session cookies over HTTPS; the production client
passed real-site login and subsequent-request acceptance on 2026-10-19. Combined search, pagination, TXT wait-page retrieval and player-compatible export
have since passed live probes. Search normalization preserves punctuation and
accents; ASCII case and whitespace handling are backed by live comparisons. The research
and roadmap documents mentioned on Trello were not provided; the snapshot only
captures card descriptions. Implement no assumptions as settled protocol facts.
