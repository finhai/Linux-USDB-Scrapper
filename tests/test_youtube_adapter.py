import asyncio
import os
import sys

import pytest

from usdb_scrapper.download_manager.media import MediaDownloadError
from usdb_scrapper.download_manager.youtube import YtDlpDownloader

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Linux adapter")
URL = "https://youtu.be/abcdefghijk"


def fake_tool(tmp_path, monkeypatch, body):
    tool = tmp_path / "yt-dlp"
    tool.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nimport sys, time\n" + body)
    tool.chmod(0o755)
    for name in ("ffmpeg", "ffprobe"):
        (tmp_path / name).symlink_to(tool)
    monkeypatch.setenv("PATH", str(tmp_path))
    return YtDlpDownloader("yt-dlp", timeout=2)


@pytest.mark.parametrize("kind", ["audio", "video"])
def test_complete_output_and_safe_arguments(tmp_path, monkeypatch, kind):
    adapter = fake_tool(
        tmp_path,
        monkeypatch,
        """
assert '--ignore-config' in sys.argv
assert '--no-playlist' in sys.argv
assert sys.argv[-2:] == ['--', 'https://www.youtube.com/watch?v=abcdefghijk']
ext = 'mp3' if '--extract-audio' in sys.argv else 'mp4'
Path('media.' + ext).write_bytes(b'media fixture')
""",
    )
    target = tmp_path / ("song.mp3" if kind == "audio" else "song.mp4")
    asyncio.run(getattr(adapter, kind)(URL, target))
    assert target.read_bytes() == b"media fixture"
    assert not list(tmp_path.glob(".usdb-media-*"))


@pytest.mark.parametrize("body", ["sys.exit(1)", "pass", "Path('media.mp3').touch()"])
def test_failed_output_cleanup(tmp_path, monkeypatch, body):
    adapter = fake_tool(tmp_path, monkeypatch, body)
    target = tmp_path / "song.mp3"
    with pytest.raises(MediaDownloadError):
        asyncio.run(adapter.audio(URL, target))
    assert not target.exists()
    assert not list(tmp_path.glob(".usdb-media-*"))


def test_existing_file_is_preserved(tmp_path, monkeypatch):
    adapter = fake_tool(tmp_path, monkeypatch, "raise AssertionError('must not launch')")
    target = tmp_path / "song.mp3"
    target.write_bytes(b"original")
    with pytest.raises(MediaDownloadError, match="already exists"):
        asyncio.run(adapter.audio(URL, target))
    assert target.read_bytes() == b"original"


def test_cancel_reaps_process_and_cleans(tmp_path, monkeypatch):
    marker = tmp_path / "started"
    adapter = fake_tool(
        tmp_path,
        monkeypatch,
        f"Path({str(marker)!r}).write_text(str(__import__('os').getpid()))\ntime.sleep(30)",
    )

    async def run():
        task = asyncio.create_task(adapter.audio(URL, tmp_path / "song.mp3"))
        async with asyncio.timeout(5):
            while not marker.exists():
                await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    with pytest.raises(ProcessLookupError):
        os.kill(int(marker.read_text()), 0)
    assert not list(tmp_path.glob(".usdb-media-*"))


def test_timeout_cleanup(tmp_path, monkeypatch):
    fake_tool(tmp_path, monkeypatch, "time.sleep(30)")
    with pytest.raises(MediaDownloadError, match="timed out"):
        asyncio.run(YtDlpDownloader("yt-dlp", timeout=0.05).audio(URL, tmp_path / "song.mp3"))
    assert not list(tmp_path.glob(".usdb-media-*"))


def test_missing_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr("usdb_scrapper.download_manager.youtube.media_tool", lambda name: None)
    with pytest.raises(MediaDownloadError, match="Install"):
        asyncio.run(YtDlpDownloader().audio(URL, tmp_path / "song.mp3"))
