# Changelog

## Unreleased

- Connect paginated search, detail enrichment, Song ID deduplication and final YouTube filtering.

- Fetch song details and extract distinct YouTube references from verified comment sections.

- Parse detailed listing rows into SongEntry records and retrieve bounded 100-result pages.

- Add combined artist/title search HTML retrieval and deterministic sort-toggle state.

- Add an in-memory USDB session client with verified login and authenticated HTML requests.

- Add an UltraStar TXT model with optional genre and opaque note-block preservation.

- Initial package structure, launchable desktop shell, locked environment, and quality checks.
- Add an immutable, validated SongEntry domain model for search-result metadata.
