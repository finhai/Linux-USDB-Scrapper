# Install and first run

## Run this checkout

From `/home/faule/MySoftware/Linux-USDB-Scrapper`:

```sh
.venv/bin/python -m usdb_scrapper
```

For a fresh clone, install uv, then run `uv sync --locked` and
`uv run usdb-scrapper`. Python and dependencies are locked by the repository.
On Linux, Qt also requires host EGL/OpenGL and xkbcommon libraries.

The app opens on Search. Enter an artist and/or title. It uses your native-keyring
credentials if available; otherwise it asks for login. Select one or more songs
and choose Download selected. Check Settings before downloading: the default
library root is `~/Music/UltraStar`. Download states and cancellation/retry are
available in Downloads. Settings changes apply without restarting.

## Desktop package

Build on the target operating system:

```sh
uv run python scripts/build_desktop.py
```

Run `dist/USDB-Scrapper/USDB-Scrapper` (Linux) or
`dist/USDB-Scrapper/USDB-Scrapper.exe` (Windows). Keep the whole directory together;
`_internal` is required. Python is included. yt-dlp is included at the uv.lock
version. Linux archives must preserve symlinks; use the supplied tar.gz format.
The packaging workflow builds Linux and Windows candidates, not signed releases.

FFmpeg and ffprobe are required for media. Install both through your OS package
manager, put them on PATH, place them in a `tools` folder next to the packaged
executable, or set `USDB_FFMPEG_DIR` to their directory. On this development
checkout only, a locally extracted Ubuntu FFmpeg package exists under
`.tools/ffmpeg/usr/bin`; it uses this machine's shared libraries and is not a
portable distributable. Those binaries are excluded from Git.

YouTube may additionally require a supported JavaScript runtime (Deno or a
supported Node version); future site changes can require updating yt-dlp.
No browser cookies or USDB credentials are supplied to YouTube.

## Compatibility and acceptance

New downloads use **VERSION 1.0.0 with AUDIO only**, preserving source BPM, timing
and notes. UltraStar Deluxe 2026.10.0 supports this header combination and rejects
VERSION 2.0.0. Previously generated draft-v2 bundles must be downloaded again;
changing their VERSION alone would corrupt timing. Actual playback remains to be checked. Video selection targets H.264 MP4 up to 1080p
and AAC audio rather than assuming every MP4 codec is supported by players.

Current evidence: offline Qt workflow and process-crash recovery pass. A live
Song 3289 bundle retrieved all four files using remembered credentials; media
streams and cover image were inspected. Linux package version/media-worker checks
pass on the development machine. Clean Windows, a second Linux distribution,
and actual UltraStar playback still require verification. Do not label this a
finished cross-platform release until those checks pass.

See [desktop behavior](desktop.md), [transaction limitations](library-recovery.md),
and [player export](player-export.md) for implementation details.

Latest evidence is recorded in [validation](validation-2026-10-22.md).


Minimal Linux systems need Qt runtime libraries. Debian/Ubuntu: install `libegl1`,
`libgl1`, `libopengl0`, `libxkbcommon0`, `libfontconfig1`, and `libdbus-1-3`.
Fedora: install `libglvnd-egl`, `libglvnd-glx`, `libglvnd-opengl`, `libxkbcommon`,
`fontconfig`, and `dbus-libs`. These cover the offscreen package smoke test;
interactive X11/Wayland sessions also need their normal desktop libraries.
