First public release for Linux and Windows.

- Fast artist/title search, sorting, automatic scroll pagination, background covers and source hints.
- Refresh and cancel search, with a 15-minute metadata cache.
- Build a download queue before starting; cancel or retry individual songs.
- Readable Artist/Title folders and title-based TXT, MP3, MP4 and JPG filenames.
- UltraStar-compatible VERSION 1.0.0 / AUDIO export with source notes and timing preserved.
- Optional native-keyring login remembered for 30 days.
- Purple interface and matching desktop/AppImage icon.

## Downloads
Linux x86-64: make the AppImage executable and launch it. Use `--appimage-extract-and-run` if FUSE is unavailable.

Windows x86-64: extract the portable ZIP and open `USDB-Scrapper/USDB-Scrapper.exe`. Keep the accompanying folders together. The executable is unsigned.

Python, Qt, yt-dlp, FFmpeg and ffprobe are bundled. SHA-256 checksum files accompany both downloads.

## Validation and known limits
539 automated tests, formatting, lint and type checks pass. Native Linux/Windows package checks and Debian/Fedora startup checks are automated. Live USDB downloads and UltraStar playback were tested on Linux; interactive Windows playback is not independently verified.

A YouTube link found in comments does not guarantee availability. Private, removed or restricted videos can fail at download time; failed items can be retried. Different versions with identical artist/title names share a destination folder. A USDB account and internet connection are required.

## Development disclaimer

This software was completely vibe coded as an experiment to test the capabilities
of AI-assisted development. It is based on an earlier, less polished version I
made myself and chose not to continue working on.

