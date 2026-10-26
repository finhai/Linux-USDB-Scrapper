# Round-trip fidelity (card 28)

ParsedTxt retains the original header lines as non-semantic source information.
Export reuses unchanged lines, preserving case, spaces, order and CR/LF endings.
Changes to model fields override retained lines. Notes remain exactly as parsed.
The source snapshot is immutable. Retained source headers are excluded from the
object representation to avoid accidentally logging private song content.

scripts/check_usdb_round_trip.py retrieves song 3289 once and tests two paths:

- Media-only rewriting: every non-media header and the note block must remain
  byte-identical when encoded as UTF-8; all three media fields must be local.
- Approved v2 conversion: notes and headers outside the explicit migration set
  must remain identical; a second export must produce identical bytes. Timing
  conversion has independent offline physical-time regression tests.

The script prints booleans or sanitized errors, not song text, and writes no
song files. Filenames are test values; no media download is implied. UTF-8 byte
comparisons start from extracted Unicode text, not the original HTTP encoding.
No claim is made that v2 migration preserves original timing-header bytes:
those changes were explicitly authorized on 2026-10-20.

Offline checks cover mixed source formatting, three newline conventions,
non-ASCII text, no terminal newline, decimal-comma BPM, metadata edits, and a
negative test proving the live checker detects an unexpected title change.
Real-file acceptance remains pending. This does not close card 24's separate
visual special-character comparison or verify player compatibility.

Live verification passed on 2026-10-21 for song 3289: all eight reported
checks were true, including unchanged non-media headers/notes, correct local
media fields, and identical second v2 export.
