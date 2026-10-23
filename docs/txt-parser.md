# TXT parser (card 25)

parse_txt returns ParsedTxt(song, extra_headers, video_metadata). The song is UltraStarTxt;
unknown headers are retained separately so later serialization can preserve GAP,
VIDEOGAP and other metadata. Notes are opaque and preserved exactly from the
first non-header line onward. Header values are trimmed, names uppercased,
and duplicates rejected. Decimal comma BPM is supported.

AUDIO takes precedence over legacy MP3. A standalone VIDEO v=<11-character ID>
is normalized to an HTTPS YouTube watch URL; literal filenames remain literal.
Comma-separated VIDEO meta-tags are supported. The v value is normalized;
co, bg and other values are preserved in video_metadata outside the domain model.
They are not interpreted as local filenames or fetched during parsing. Missing VERSION and COVER values remain None, matching the observed live
legacy file. An explicit caller default can fill them when desired; VIDEO still
requires a value or explicit default. No source metadata is invented. No files are accessed and no tags are rewritten to local filenames.

Synthetic tests cover legacy/modern equivalence, body preservation, unknown
headers, invalid metadata and explicit default policy. Real-file parsing acceptance passed on 2026-10-20 for song 3289. scripts/check_usdb_parser.py reports only booleans and missing required
field names; it never prints lyrics or credentials. Card 24's special-character
comparison remains separate and pending.

Live check on 2026-10-20 found MP3 and VIDEO meta-tags but no VERSION or COVER.
The initial parser rejected that file. The model and parser now allow those two
fields to be absent; a synthetic regression reproduces that header combination.
All 284 tests, lint, strict typing and the offline build pass.

A second live check identified a compound VIDEO value with v, co and bg keys.
The parser now supports this syntax; synthetic tests verify preservation and
rejection of empty/duplicate tags. The subsequent live rerun passed: parsed=true, positive BPM, nonempty note
block, absent VERSION/COVER retained as None, and two auxiliary video metadata
values retained. Legacy/modern equivalence and exact note preservation are
covered by synthetic tests; the live report verifies successful parsing.
