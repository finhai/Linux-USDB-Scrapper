# USDB Scrapper

A purple-themed desktop app for finding USDB songs and building an UltraStar
library on Linux and Windows.

## Features

- Search by artist, title, or both, with sorting and automatic pagination.
- See results as soon as the listing arrives; cover previews and comment-link
  checks load in the background. Songs are never hidden just because a comment
  link has not been found.
- Repeat searches use a bounded, 15-minute in-memory cache. **Refresh results**
  bypasses cached search/source information. Changing a search cancels its old work.
- Add songs to a queue, then explicitly start the batch. Cancel and retry individual
  downloads; see clear queue confirmation and stage-specific errors.
- Download TXT, MP3, MP4 and JPG files into readable `Artist/Title/` folders.
  Filenames and TXT media references use the song title.
- Export player-compatible `#VERSION:1.0.0` and `#AUDIO`, preserving source timing
  and notes. Downloads support YouTube audio/video source metadata.
- Optionally remember login in the operating system's native keyring for **30 days**.
  Automatic sign-in does not extend that period.

## Download and run

Download **[USDB Scrapper 1.0.0](https://github.com/finhai/Linux-USDB-Scrapper/releases/tag/v1.0.0)**:

| Platform | Download |
| --- | --- |
| Linux x86-64 | [AppImage](https://github.com/finhai/Linux-USDB-Scrapper/releases/download/v1.0.0/USDB-Scrapper-1.0.0-x86_64.AppImage) |
| Windows x86-64 | [Portable ZIP with EXE](https://github.com/finhai/Linux-USDB-Scrapper/releases/download/v1.0.0/USDB-Scrapper-1.0.0-windows-x86_64.zip) |

SHA-256 checksum files accompany both downloads. No Python installation is needed.

**Linux:** make the `.AppImage` executable and open it. If FUSE is unavailable,
run it with `--appimage-extract-and-run`.

**Windows:** extract the portable ZIP, then launch `USDB-Scrapper.exe` from its
`USDB-Scrapper` folder. Keep `_internal`, `tools` and the other bundled files together.
The executable is unsigned.

Release packages include Python, Qt, yt-dlp, FFmpeg and ffprobe. A USDB account,
internet connection and graphical desktop are required. Remembering login also
requires a working native keyring. See [installation and troubleshooting](docs/install.md).

## First use

1. Sign in with your USDB account. Choose **Remember me for 30 days** if desired.
2. In **Settings**, choose your song-library directory, such as `/mnt/Storage/Songs`.
3. Search for an artist or title. Scroll down to fetch further results automatically.
   The status changes to **All results loaded** at the end. A failed page exposes
   **Retry loading results** without discarding the rows already shown.
4. Select songs and choose **Add to queue**. Open **Downloads**, then choose
   **Start queued downloads** when ready.
5. Add the library directory to UltraStar Deluxe's song directories.

A **YouTube link found** status means a link was found in USDB comments, not that
YouTube playback has been verified. **Check on download** is not an exclusion:
TXT metadata may supply a usable source. Actual media availability is established
when downloading. Private, removed or restricted media can still fail. Failed
items remain in the queue for retry; incomplete staging files are cleaned up.
The app does not substitute a different video automatically.

## Development

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
uv sync --locked
uv run usdb-scrapper
```

Quality checks and Python package builds:

```sh
uv run python scripts/check.py
uv build
```

Native release packages must be built on their target operating system:

```sh
uv run python scripts/build_desktop.py
uv run python scripts/check_package.py
uv run python scripts/package_release.py
```

See [contributing](CONTRIBUTING.md), [architecture](docs/architecture.md),
[release workflow](docs/releases.md), and the
[Trello roadmap](https://trello.com/b/KnffFXKA/usdb-scrapper-linux).

## Validation and limitations

Automated checks cover Linux and Windows, desktop interactions, native packaging,
and Linux startup in Debian/Fedora containers. Live USDB checks cover login,
pagination, TXT retrieval and media downloads; playback has been exercised during
user testing. Automated startup checks do not replace interactive Windows acceptance.

The application supports YouTube media sources, not every external source on USDB.
Site changes can require updates. Song replacement is staged with crash recovery;
it is not a guarantee against power loss. Different versions with the same artist
and title share a destination name: a queue rejects two jobs targeting that same folder.

## Reporting problems

[Open an issue](https://github.com/finhai/Linux-USDB-Scrapper/issues) with your OS,
app version, song ID, and the visible error message. Never include passwords or
session cookies.
