# Download Item contract

Card #11 adds DownloadItem, DownloadBundle, DownloadState, and
InvalidDownloadTransition in `usdb_scrapper.domain.download_item`.

A job pairs one SongEntry with four target paths: txt (.txt), audio (.mp3),
video (.mp4), and cover (.jpg). Paths are PurePath values (including Windows or
POSIX variants). Only their types and suffixes are checked. No paths are opened,
resolved, created, or inspected. Naming, containment, staging, and actual file
completion are the future Storage/Download Managers' responsibilities.

New jobs start QUEUED. Allowed transitions are:

- QUEUED → DOWNLOADING
- DOWNLOADING → COMPLETED or FAILED
- FAILED → RETRY
- RETRY → QUEUED

COMPLETED is terminal. Repeated or skipped transitions raise
InvalidDownloadTransition (a ValueError subclass). RETRY is a request to requeue;
it does not bypass queue scheduling or concurrency limits. FAILED requires a
nonblank error message. Entering RETRY clears that message in the new snapshot;
the previous immutable FAILED snapshot retains it.

Use `updated = item.transition(DownloadState.DOWNLOADING)`. This returns a new
frozen snapshot and preserves the song and bundle references. The caller owns
replacing its current snapshot; queue synchronization belongs to the manager.
Constructing a snapshot directly is allowed for future restoration, but still
validates state/error consistency. This does not validate historical transitions.

COMPLETED records the manager's assertion that all four files are ready; the
model cannot verify that assertion without I/O. It also does not require a
resolved YouTube link to represent a queued song. Cancellation, progress,
retry policies, persistence, and real downloading belong to later cards.
