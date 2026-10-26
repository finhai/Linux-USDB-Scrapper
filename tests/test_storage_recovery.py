import os
import subprocess
import sys

import pytest

from usdb_scrapper.domain.download_item import DownloadBundle
from usdb_scrapper.storage_manager.bundle import (
    BundleStage,
    BundleStorageError,
    identical,
    recover_directory,
)


def bundle(root):
    return DownloadBundle(
        txt=root / "song.txt",
        audio=root / "song.mp3",
        video=root / "song.mp4",
        cover=root / "song.jpg",
    )


def fill(stage, value):
    for path in stage.paths.values():
        path.write_bytes(value)


def test_identical_skips_and_changed_bundle_replaces(tmp_path):
    root = tmp_path / "song"
    first = BundleStage(bundle(root))
    fill(first, b"original")
    first.publish()
    stamp = (root / "song.mp3").stat().st_mtime_ns
    second = BundleStage(bundle(root))
    fill(second, b"original")
    second.publish()
    assert (root / "song.mp3").stat().st_mtime_ns == stamp
    third = BundleStage(bundle(root))
    fill(third, b"changed")
    assert (root / "song.mp3").read_bytes() == b"original"
    third.publish()
    assert all(path.read_bytes() == b"changed" for path in root.iterdir())
    assert not list(tmp_path.glob(".usdb-txn-*"))
    assert not list(tmp_path.glob(".usdb-backup-*"))


@pytest.mark.parametrize("phase", ["staging", "replacing", "published"])
def test_kill_and_restart_recovers_complete_directory(tmp_path, phase):
    root = tmp_path / "song"
    first = BundleStage(bundle(root))
    fill(first, b"original")
    first.publish()
    script = """
import sys, time, os
from pathlib import Path
import usdb_scrapper.storage_manager.bundle as module
from usdb_scrapper.domain.download_item import DownloadBundle
from usdb_scrapper.storage_manager.bundle import BundleStage
root = Path(sys.argv[1])
s = BundleStage(DownloadBundle(txt=root/'song.txt', audio=root/'song.mp3',
                               video=root/'song.mp4', cover=root/'song.jpg'))
for path in s.paths.values(): path.write_bytes(b'changed')
def pause():
    print('ready', flush=True)
    time.sleep(60)
if sys.argv[2] == 'staging': pause()
if sys.argv[2] == 'replacing':
    original = os.replace
    def replacement(source, destination):
        original(source, destination)
        if Path(destination) == root/'song.mp3': pause()
    os.replace = replacement
if sys.argv[2] == 'published':
    original_recover = module._recover
    def recover(journal):
        pause()
        original_recover(journal)
    module._recover = recover
s.publish()
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(root), phase], stdout=subprocess.PIPE
    )
    try:
        assert process.stdout.readline().strip() == b"ready"
        # Active transactions must not be removed by another instance.
        assert recover_directory(tmp_path) == 0
        process.kill()
        process.wait(timeout=5)
        assert recover_directory(tmp_path) == 1
        expected = b"changed" if phase == "published" else b"original"
        assert len(list(root.iterdir())) == 4
        assert all(path.read_bytes() == expected for path in root.iterdir())
        assert not list(tmp_path.glob(".usdb-partial-*"))
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()


def test_unknown_journal_does_not_delete_files(tmp_path):
    sentinel = tmp_path / "important"
    sentinel.mkdir()
    (sentinel / "data").write_text("keep")
    (tmp_path / ".usdb-txn-song.json").write_text('{"destination":"../important","token":"bad"}')
    with pytest.raises(BundleStorageError):
        recover_directory(tmp_path)
    assert (sentinel / "data").read_text() == "keep"


def test_large_file_comparison(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    data = os.urandom(2_500_000)
    first.write_bytes(data)
    second.write_bytes(data)
    assert identical(first, second)
    with second.open("r+b") as stream:
        stream.seek(1_500_000)
        value = stream.read(1)[0]
        stream.seek(-1, 1)
        stream.write(bytes([value ^ 1]))
    assert not identical(first, second)
