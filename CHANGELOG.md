# Changelog

## Unreleased

- Export new downloads as player-compatible VERSION 1.0.0 with AUDIO only and unchanged timing.

- Connect deferred login, paginated search, download controls and settings to the desktop.
- Integrate native credential recovery, portable library paths and atomic preference saves.
- Recover interrupted library transactions and skip identical completed bundles.
- Lock yt-dlp with project dependencies and add native desktop packaging builds.


- Support queue cancellation, clean retries, and per-item bundle stage reporting.

- Add a replaceable media interface and Linux yt-dlp adapter with timeout/cancellation cleanup; live conversion and Windows support pending.

- Add staged four-file bundle orchestration with completeness checks and failure cleanup; live media adapters pending.

- Add FIFO download scheduling with adjustable concurrency and per-item completion/failure states.

- Add explicit native-keyring credential setup and automatic reuse in manual USDB checks.

- Preserve unchanged source header formatting and add media-only/v2 round-trip fidelity checks.

- Add opt-in draft-v2 UTF-8 export with explicit timing migration and unchanged note text.

- Export TXT with local media filenames while preserving notes and rejecting residual YouTube references.

- Preserve missing source VERSION and COVER metadata as None when parsing legacy files.

- Parse TXT headers into the song model, normalize legacy MP3/video tags, and preserve notes and extra headers.

- Extract raw TXT payloads with single-pass HTML entity decoding and strict response encoding handling.

- Add bounded TXT wait-page retrieval; live wait/POST sequence verified.

- Connect paginated search, detail enrichment, Song ID deduplication and final YouTube filtering.

- Fetch song details and extract distinct YouTube references from verified comment sections.

- Parse detailed listing rows into SongEntry records and retrieve bounded 100-result pages.

- Add combined artist/title search HTML retrieval and deterministic sort-toggle state.

- Add an in-memory USDB session client with verified login and authenticated HTML requests.

- Add an UltraStar TXT model with optional genre and opaque note-block preservation.

- Initial package structure, launchable desktop shell, locked environment, and quality checks.
- Add an immutable, validated SongEntry domain model for search-result metadata.
