"""Linux yt-dlp CLI adapter, isolated from queue and bundle orchestration."""

import asyncio
import os
import shutil
import signal
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import psutil

from usdb_scrapper.download_manager.media import MediaDownloadError
from usdb_scrapper.usdb_client.details import youtube_url


def media_tool(name: str) -> str | None:
    """Prefer explicit/local tools, then the system PATH."""
    suffix = ".exe" if os.name == "nt" else ""
    locations = [
        Path(sys.executable).parent / "tools",
        Path(__file__).resolve().parents[3] / ".tools" / "ffmpeg" / "usr" / "bin",
    ]
    if os.environ.get("USDB_FFMPEG_DIR"):
        locations.insert(0, Path(os.environ["USDB_FFMPEG_DIR"]))
    for folder in locations:
        candidate = folder / (name + suffix)
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


class YtDlpDownloader:
    """Uses explicitly installed yt-dlp and FFmpeg; never loads user CLI config.

    POSIX process groups allow cancellation to stop conversion subprocesses too.
    Windows support requires a process-tree lifecycle implementation first.
    """

    def __init__(self, executable: str | None = None, *, timeout: float = 1800) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._executable = executable
        self._timeout = timeout

    async def audio(self, url: str, target: Path) -> None:
        await self._download(url, target, "mp3")

    async def video(self, url: str, target: Path) -> None:
        await self._download(url, target, "mp4")

    async def _download(self, url: str, target: Path, extension: str) -> None:
        canonical = youtube_url(url)
        if canonical is None or target.suffix != f".{extension}":
            raise MediaDownloadError("Invalid YouTube reference or media target")
        if self._executable is not None:
            executable = shutil.which(self._executable)
            if executable is None:
                raise MediaDownloadError("The configured downloader is unavailable")
            command = [executable]
        elif getattr(sys, "frozen", False):
            command = [sys.executable, "--media-worker"]
        else:
            command = [sys.executable, "-m", "yt_dlp"]
        ffmpeg = media_tool("ffmpeg")
        if ffmpeg is None or media_tool("ffprobe") is None:
            raise MediaDownloadError("Install FFmpeg and ffprobe before downloading")
        if target.exists() or target.is_symlink():
            raise MediaDownloadError("Media target already exists")
        try:
            with TemporaryDirectory(prefix=".usdb-media-", dir=target.parent) as temporary:
                folder = Path(temporary)
                args = [
                    *command,
                    "--ignore-config",
                    "--no-plugin-dirs",
                    "--no-playlist",
                    "--no-progress",
                    "--no-warnings",
                    "--socket-timeout",
                    "30",
                    "--retries",
                    "3",
                    "--ffmpeg-location",
                    ffmpeg,
                    "--output",
                    "media.%(ext)s",
                ]
                if extension == "mp3":
                    args += [
                        "--format",
                        "bestaudio/best",
                        "--extract-audio",
                        "--audio-format",
                        "mp3",
                    ]
                else:
                    args += [
                        "--format",
                        "bestvideo[ext=mp4][vcodec^=avc1][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][vcodec^=avc1][height<=1080]",
                        "--merge-output-format",
                        "mp4",
                    ]
                args += ["--", canonical]
                process = await asyncio.create_subprocess_exec(
                    *args,
                    cwd=folder,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    start_new_session=os.name == "posix",
                )
                try:
                    async with asyncio.timeout(self._timeout):
                        result = await process.wait()
                finally:
                    # Also stop descendants if the parent exited before cancellation.
                    if os.name == "posix":
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    elif process.returncode is None:
                        try:
                            parent = psutil.Process(process.pid)
                            parent.suspend()
                            for child in parent.children(recursive=True):
                                try:
                                    child.kill()
                                except psutil.NoSuchProcess:
                                    pass
                            parent.kill()
                        except psutil.NoSuchProcess:
                            pass
                    await process.wait()
                output = folder / f"media.{extension}"
                if result != 0 or output.is_symlink() or not output.is_file():
                    raise MediaDownloadError("YouTube download failed")
                if output.stat().st_size == 0:
                    raise MediaDownloadError("YouTube produced empty media")
                # A hard link publishes without overwriting an existing target.
                os.link(output, target)
        except (OSError, TimeoutError):
            raise MediaDownloadError("Media download failed or timed out") from None
