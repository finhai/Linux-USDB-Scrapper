# Draft v2 serialization (card 27)

User decision, 2026-10-20: target the unpublished 2.0.0 draft, with AUDIO only
and explicit timing conversion. This replaces the card's ambiguous reference
to the published spec. Reference documents reviewed that date:

- https://github.com/UltraStar-Deluxe/format/blob/main/The%20UltraStar%20File%20Format%20(v1).md
- https://github.com/UltraStar-Deluxe/format/blob/main/The%20UltraStar%20File%20Format%20(v2).md

serialize_v2_txt(parsed, media) returns UTF-8 bytes without BOM. The required
VERSION, TITLE, ARTIST, BPM and AUDIO headers are emitted; VIDEO and COVER use
caller-supplied local filenames. Explicit voice changes require matching Pn
labels. It preserves the note block exactly and never writes files itself.

Unversioned input is treated as legacy timing, as are 1.0.0 and 1.1.0: BPM is
multiplied by four; START, VIDEOGAP and PREVIEWSTART seconds become milliseconds.
GAP and END remain milliseconds. Medley beat positions become milliseconds,
including GAP. Fractions that cannot be represented exactly are rejected.
Input already labeled 2.0.0 is not converted again. Unknown versions and legacy
RELATIVE/RESOLUTION flags fail rather than guessing. ENCODING is omitted.

This checks required fields, encoding and supported timing conversion. It is
not a full musical-grammar validator and does not prove playback compatibility.
The draft can change. Version migration intentionally changes timing headers;
card 28's byte-for-byte comparison must account for this explicitly authorized
conversion as well as media-field changes. Raw source metadata stays unchanged.

Validation: offline required-field, Unicode, exact-body, physical-time,
idempotence, duet-label and rejected-conversion tests; no live credentials needed.
