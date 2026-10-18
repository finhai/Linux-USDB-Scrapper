"""Exercise the whole lifecycle independently of network and filesystem state."""

from dataclasses import FrozenInstanceError, replace
from pathlib import PurePosixPath, PureWindowsPath

import pytest

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.domain.download_item import (
    DownloadBundle,
    DownloadItem,
    DownloadState,
    InvalidDownloadTransition,
)


@pytest.fixture
def bundle():
    return DownloadBundle(
        txt=PurePosixPath("artist/song/song.txt"),
        audio=PurePosixPath("artist/song/song.mp3"),
        video=PurePosixPath("artist/song/song.mp4"),
        cover=PurePosixPath("artist/song/song.jpg"),
    )


@pytest.fixture
def job(bundle):
    return DownloadItem(song=SongEntry(song_id=42, artist="Artist", title="Song"), bundle=bundle)


def test_success_path_retains_song_and_bundle(job):
    active = job.transition(DownloadState.DOWNLOADING)
    completed = active.transition(DownloadState.COMPLETED)
    assert job.state is DownloadState.QUEUED
    assert active.state is DownloadState.DOWNLOADING
    assert completed.state is DownloadState.COMPLETED
    assert completed.song is job.song
    assert completed.bundle is job.bundle
    assert completed.error is None


def test_failure_retry_requeues_and_clears_previous_error(job):
    failed = job.transition(DownloadState.DOWNLOADING).transition(
        DownloadState.FAILED,
        error="Transfer interrupted",
    )
    retry = failed.transition(DownloadState.RETRY)
    assert failed.error == "Transfer interrupted"
    assert retry.error is None
    queued = retry.transition(DownloadState.QUEUED)
    completed = queued.transition(DownloadState.DOWNLOADING).transition(DownloadState.COMPLETED)
    assert completed.state is DownloadState.COMPLETED
    assert completed.song is job.song
    assert completed.bundle is job.bundle


@pytest.mark.parametrize("source", list(DownloadState))
@pytest.mark.parametrize("target", list(DownloadState))
def test_transition_matrix(job, source, target):
    allowed = {
        (DownloadState.QUEUED, DownloadState.DOWNLOADING),
        (DownloadState.DOWNLOADING, DownloadState.COMPLETED),
        (DownloadState.DOWNLOADING, DownloadState.FAILED),
        (DownloadState.FAILED, DownloadState.RETRY),
        (DownloadState.RETRY, DownloadState.QUEUED),
    }
    snapshot = replace(
        job, state=source, error="Failed" if source is DownloadState.FAILED else None
    )
    if (source, target) in allowed:
        result = snapshot.transition(
            target, error="Failed" if target is DownloadState.FAILED else None
        )
        assert result.state is target
    else:
        with pytest.raises(InvalidDownloadTransition):
            snapshot.transition(target)
    assert snapshot.state is source


@pytest.mark.parametrize(
    "error,exception", [(None, TypeError), (42, TypeError), ("", ValueError), (" \t", ValueError)]
)
def test_failure_requires_explanation(job, error, exception):
    active = job.transition(DownloadState.DOWNLOADING)
    with pytest.raises(exception, match="error"):
        active.transition(DownloadState.FAILED, error=error)
    assert active.state is DownloadState.DOWNLOADING


def test_errors_cannot_leak_into_other_states(job):
    with pytest.raises(ValueError, match="error"):
        job.transition(DownloadState.DOWNLOADING, error="stale error")


@pytest.mark.parametrize("field,value", [("song", None), ("bundle", None), ("state", "queued")])
def test_invalid_snapshots_rejected(job, field, value):
    with pytest.raises(TypeError, match=field):
        replace(job, **{field: value})


def test_invalid_target_type_rejected(job):
    with pytest.raises(TypeError, match="state"):
        job.transition("downloading")


def test_snapshots_cannot_be_mutated(job):
    with pytest.raises(FrozenInstanceError):
        job.state = DownloadState.COMPLETED
    with pytest.raises(FrozenInstanceError):
        job.bundle.txt = PurePosixPath("other.txt")


@pytest.mark.parametrize(
    "field,suffix", [("txt", "txt"), ("audio", "mp3"), ("video", "mp4"), ("cover", "jpg")]
)
def test_bundle_validates_each_target(bundle, field, suffix):
    with pytest.raises(TypeError, match=field):
        replace(bundle, **{field: f"song.{suffix}"})
    with pytest.raises(ValueError, match=field):
        replace(bundle, **{field: PurePosixPath("song.wrong")})
    upper = PureWindowsPath(f"C:/Library/Song.{suffix.upper()}")
    assert getattr(replace(bundle, **{field: upper}), field) == upper


def test_bundle_does_not_require_real_files_or_resolve_paths():
    bundle = DownloadBundle(
        txt=PureWindowsPath("Z:/nonexistent/song.txt"),
        audio=PureWindowsPath("Z:/nonexistent/song.mp3"),
        video=PureWindowsPath("Z:/nonexistent/song.mp4"),
        cover=PureWindowsPath("Z:/nonexistent/song.jpg"),
    )
    assert str(bundle.txt) == "Z:\\nonexistent\\song.txt"
