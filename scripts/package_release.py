"""Package the native PyInstaller output with pinned, verified media tools."""

import hashlib
import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import httpx

from usdb_scrapper import __version__

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
CACHE = ROOT / ".tools" / "release-downloads"
FFMPEG_BASE = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/autobuild-2026-10-24-17-20/"
)
FFMPEG = {
    "linux": (
        "ffmpeg-N-128018-ga881f0a9ad-linux64-gpl.tar.xz",
        "6623a690faaded21ae08caf8bcc49ec077a5647ab4c0347e4064d9f2b2ce23b7",
    ),
    "windows": (
        "ffmpeg-N-128018-ga881f0a9ad-win64-gpl.zip",
        "80418b69fbf11a7db0b06e2c4ea8cbf1c742c91ace4f4295577c6bea6ab0c35e",
    ),
}


def download(url: str, digest: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / url.rsplit("/", 1)[-1]
    if not target.exists():
        temporary = target.with_suffix(".download")
        with httpx.stream("GET", url, follow_redirects=True, timeout=120) as response:
            response.raise_for_status()
            with temporary.open("wb") as stream:
                for chunk in response.iter_bytes():
                    stream.write(chunk)
        temporary.replace(target)
    with target.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != digest:
        raise ValueError(f"Checksum mismatch for {target.name}")
    return target


def media_tools(package: Path) -> None:
    platform = "windows" if os.name == "nt" else "linux"
    filename, digest = FFMPEG[platform]
    archive = download(FFMPEG_BASE + filename, digest)
    tools = package / "tools"
    tools.mkdir(exist_ok=True)
    licenses = package / "licenses" / "ffmpeg"
    licenses.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if os.name == "nt" else ""
    binaries = {"ffmpeg" + suffix, "ffprobe" + suffix}

    def save(name: str, data: bytes) -> None:
        leaf = Path(name).name
        if leaf in binaries:
            target = tools / leaf
            target.write_bytes(data)
            target.chmod(0o755)
        elif "license" in name.lower() or "readme" in leaf.lower():
            (licenses / leaf).write_bytes(data)

    if os.name == "nt":
        with zipfile.ZipFile(archive) as zipped:
            for entry in zipped.infolist():
                if not entry.is_dir():
                    save(entry.filename, zipped.read(entry))
    else:
        with tarfile.open(archive) as tar:
            for entry in tar:
                if entry.isfile():
                    stream = tar.extractfile(entry)
                    assert stream is not None
                    save(entry.name, stream.read())
    for binary in binaries:
        subprocess.run([str(tools / binary), "-version"], check=True, stdout=subprocess.DEVNULL)
    (licenses / "SOURCE.txt").write_text(
        "FFmpeg build: " + FFMPEG_BASE + filename + "\n"
        "Build scripts and source revisions: https://github.com/yt-dlp/FFmpeg-Builds\n"
        "FFmpeg source revision: https://github.com/FFmpeg/FFmpeg/commit/a881f0a9ad\n"
        "These separate executables retain their upstream GPL licenses.\n",
        encoding="utf-8",
    )


def main() -> None:
    package = DIST / "USDB-Scrapper"
    media_tools(package)
    if os.name == "nt":
        artifact = Path(
            shutil.make_archive(
                str(DIST / f"USDB-Scrapper-{__version__}-windows-x86_64"),
                "zip",
                root_dir=DIST,
                base_dir="USDB-Scrapper",
            )
        )
    else:
        appdir = ROOT / "build" / "USDB-Scrapper.AppDir"
        if appdir.exists():
            shutil.rmtree(appdir)
        shutil.copytree(package, appdir / "usr" / "lib" / "usdb-scrapper")
        (appdir / "AppRun").write_text(
            '#!/bin/sh\nHERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\n'
            'exec "$HERE/usr/lib/usdb-scrapper/USDB-Scrapper" "$@"\n',
            encoding="utf-8",
        )
        (appdir / "AppRun").chmod(0o755)
        (appdir / "usdb-scrapper.desktop").write_text(
            "[Desktop Entry]\nName=USDB Scrapper\nExec=USDB-Scrapper\n"
            "Icon=usdb-scrapper\nStartupWMClass=usdb-scrapper\nType=Application\nCategories=AudioVideo;Audio;\nTerminal=false\n",
            encoding="utf-8",
        )
        shutil.copyfile(
            ROOT / "src/usdb_scrapper/frontend/assets/usdb-scrapper.svg",
            appdir / "usdb-scrapper.svg",
        )
        tool = download(
            "https://github.com/AppImage/appimagetool/releases/download/1.9.1/"
            "appimagetool-x86_64.AppImage",
            "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0",
        )
        tool.chmod(0o755)
        destination = DIST / f"USDB-Scrapper-{__version__}-x86_64.AppImage"
        artifact = destination.with_name(destination.stem + ".building.AppImage")
        subprocess.run(
            [str(tool), "--appimage-extract-and-run", str(appdir), str(artifact)],
            check=True,
            env={**os.environ, "ARCH": "x86_64"},
        )
        environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        for arguments in (["--version"], ["--smoke-test"]):
            subprocess.run(
                [str(artifact), "--appimage-extract-and-run", *arguments],
                check=True,
                timeout=120,
                env=environment,
            )
        artifact.replace(destination)
        artifact = destination
    with artifact.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    artifact.with_suffix(artifact.suffix + ".sha256").write_text(
        f"{digest}  {artifact.name}\n", encoding="utf-8"
    )
    print(artifact)


if __name__ == "__main__":
    main()
