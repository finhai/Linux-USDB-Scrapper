# UltraStar TXT model

Card #10 provides `UltraStarTxt` in `usdb_scrapper.domain.ultrastar_txt`.
It holds file metadata and the note/phrase block in memory. It has no dependency
on SongEntry, the USDB client, the UI, storage, or the parser.

Required fields: version, title, artist, audio, bpm, video, cover, note_block.
Genre defaults to None; absent genre is valid. Video and cover are required by
this application's bundle contract, even though the file format permits omission.
The later parser/orchestrator must resolve missing app-required media references
before constructing this normalized model; this is not a raw input document.

Header text is preserved exactly. Nonblank single-line values are required when
present, and version must have a numeric three-part shape. BPM uses Decimal to
avoid binary floating-point rounding and must be finite and positive. The parser
will decode textual numbers, including locale-specific separators. The model
neither interprets legacy headers nor translates media tags or version semantics.
Media references are strings; the model does not access paths or validate whether
files exist. It does not establish that media references are safe output paths.

The note_block is an immutable string copied unchanged through metadata updates
with dataclasses.replace. It may contain any line endings, whitespace, Unicode,
voice markers, or unknown text. Even an empty block can be represented: validating
musical syntax belongs to the parser. Tests compare UTF-8 bytes before and after
media-reference updates. This guarantees preservation of the supplied text, not
round-trip fidelity of an original file's encoding or header formatting.

TypeError indicates wrong input types; ValueError indicates invalid field values.
No parsing, serialization, note manipulation, or filesystem/network I/O is added.
The model is frozen and keyword-only. Supporting additional headers and retaining
source layout (including timing headers such as GAP) for full-file round trips
remains part of the parser design; this model alone is not a lossless file editor.

## Format reference

[Official specifications](https://github.com/UltraStar-Deluxe/format) distinguish
v1 from v2. This model carries the version supplied by the parser, and never
changes BPM or claims support for parsing a version merely by storing it.
Format compatibility and conversion must be explicitly implemented and tested
in the parser phase before writing files. In particular, a header rename alone
is not sufficient to claim a valid conversion between versions.
