# Validation record — 2026-10-22

- 493 offline tests pass, including the real Qt/controller workflow with synthetic
  external services, cancellation/retry, native-keyring fallback, session recovery,
  and process-kill recovery. Ruff and strict mypy pass; wheel/source builds pass.
- Saved Linux credentials were loaded and verified without prompting.
- A real desktop controller/view flow searched ABBA + Dancing Queen, selected
  Song 3289, queued it and completed all four files. The initial restricted-codec
  attempt failed cleanly; a repeat passed. This was not diagnosed as a deterministic
  application bug and is not evidence that network/media failures cannot recur.
- ffprobe verified MP3 audio and H.264 1920x1080 + AAC video; Pillow verified JPEG.
  Exported TXT uses VERSION 2.0.0 and local AUDIO/VIDEO/COVER, with no YouTube URL.
  No credentials, cookies or song lyrics are included in this record or Git.
- Local Linux PyInstaller package passes app-version, bundled yt-dlp-version,
  and offscreen GUI startup/shutdown. A shutdown segmentation fault was corrected
  by destroying Qt objects before interpreter teardown and waiting for the worker.
- GitHub PR 16 initial CI passed Linux/Windows tests and both native package builds.
  Those first package jobs only tested version output. Updated GUI smoke checks
  and fresh distribution/container checks are tracked separately.
- Live normalization: Dancing Queen / dancing queen return the same six IDs;
  Dáncing Quéen, doubled internal spaces and outer spaces return no rows. Therefore
  search normalization trims/collapses whitespace and normalizes ASCII case while
  preserving accents and punctuation. Broad transliteration is not assumed.

Per-file replacement now keeps final paths present and restores the original
bundle after an interrupted replacement. Process-kill recovery tests pass.

Remaining release acceptance: clean Windows GUI/credential/media behavior, two distinct Linux distributions,
actual UltraStar playback (the latest 2026.10.0 player rejects v2; version 1.0.0 AUDIO-only export is now selected and implemented), and final review/merge. The project is not yet
claimed finished or ready for a production release.
