# Local media export (card 26)

serialize_local_txt(parsed, LocalMedia(audio=..., video=..., cover=...)) returns
text with local AUDIO, VIDEO and COVER filenames. It preserves other metadata,
unknown headers (including GAP), and the exact note-block string. It drops
legacy MP3 and auxiliary VIDEO download directives from output. The input
snapshot is unchanged. Missing VERSION stays omitted.

The caller supplies filenames of downloaded files. This stage neither downloads
nor checks file existence; storage/controller integration is still outstanding.
Only plain filenames are accepted, not URLs, absolute paths or subdirectories.
Output headers use LF; the note block retains its original line endings.

Export rejects preserved text containing YouTube hostnames, video meta-tags or
the known source video ID instead of deleting lyrics or metadata. Offline tests
verify round-trip parsing, local references, exact note preservation, timing
metadata, and rejection of residual references in titles, extra headers and notes.

Acceptance limitation: an arbitrary, unrelated bare 11-character string cannot
be identified as a YouTube ID without context. The card's absolute wording
("anywhere, under any input condition") cannot be guaranteed by this detector.
Known source IDs and recognizable URL/meta-tag forms are guarded. Keep the card
in Testing until this interpretation and actual downloaded-file integration are
reviewed. General version migration/serialization policy is separate work.
