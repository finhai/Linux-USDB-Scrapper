"""Download-job data and lifecycle; no downloading or filesystem operations."""

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import PurePath

from usdb_scrapper.domain.song_entry import SongEntry


class DownloadState(Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class InvalidDownloadTransition(ValueError):
    """A requested lifecycle step is not allowed from the current state."""


@dataclass(frozen=True, slots=True, kw_only=True)
class DownloadBundle:
    """Four target paths supplied by storage; PurePath never performs I/O.

    Paths are not resolved, created, sanitized, or checked for existence here.
    Storage is responsible for containment, naming, and atomic finalization.
    """

    txt: PurePath
    audio: PurePath
    video: PurePath
    cover: PurePath

    def __post_init__(self) -> None:
        for name, suffix in (
            ("txt", ".txt"),
            ("audio", ".mp3"),
            ("video", ".mp4"),
            ("cover", ".jpg"),
        ):
            path = getattr(self, name)
            if not isinstance(path, PurePath):
                raise TypeError(f"{name} must be a PurePath")
            if path.suffix.lower() != suffix:
                raise ValueError(f"{name} must have the {suffix} suffix")


_ALLOWED = {
    DownloadState.QUEUED: frozenset({DownloadState.DOWNLOADING}),
    DownloadState.DOWNLOADING: frozenset({DownloadState.COMPLETED, DownloadState.FAILED}),
    DownloadState.FAILED: frozenset({DownloadState.RETRY}),
    DownloadState.RETRY: frozenset({DownloadState.QUEUED}),
    DownloadState.COMPLETED: frozenset(),
}


@dataclass(frozen=True, slots=True, kw_only=True)
class DownloadItem:
    """Immutable job snapshot. Call transition() and keep its returned snapshot.

    FAILED requires a nonblank error message; every other state has no error.
    RETRY explicitly returns to QUEUED so the manager's concurrency limit applies.
    Direct construction can restore any valid snapshot, without inventing history.
    """

    song: SongEntry
    bundle: DownloadBundle
    state: DownloadState = DownloadState.QUEUED
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.song, SongEntry):
            raise TypeError("song must be a SongEntry")
        if not isinstance(self.bundle, DownloadBundle):
            raise TypeError("bundle must be a DownloadBundle")
        if not isinstance(self.state, DownloadState):
            raise TypeError("state must be a DownloadState")
        if self.state is DownloadState.FAILED:
            if not isinstance(self.error, str):
                raise TypeError("error must be a string for FAILED")
            if not self.error.strip():
                raise ValueError("error must not be blank for FAILED")
        elif self.error is not None:
            raise ValueError("error is only allowed for FAILED")

    def transition(self, state: DownloadState, *, error: str | None = None) -> "DownloadItem":
        """Return a validated next state, leaving this snapshot untouched."""
        if not isinstance(state, DownloadState):
            raise TypeError("state must be a DownloadState")
        if state not in _ALLOWED[self.state]:
            raise InvalidDownloadTransition(
                f"Cannot transition from {self.state.name} to {state.name}"
            )
        return replace(self, state=state, error=error)
