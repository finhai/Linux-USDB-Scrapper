# Filesystem naming contract (card 13)

`normalize_filesystem_name` in `usdb_scrapper.normalization.filesystem` returns
one directory component or extensionless filename stem. It performs no I/O and
shares no code with search normalization. Pass original artist/title text, never
an already-normalized name. The function is deterministic, not idempotent.

Naming algorithm v1:

1. Normalize the input to NFC for canonical Unicode equivalence.
2. Produce a readable prefix using NFKD, case folding, and ASCII letters/digits;
   keep at most 24 characters. Use `item` if nothing remains.
3. Return `n` + prefix + `x` + the first 32 hexadecimal characters of SHA-256
   over the full NFC UTF-8 input. Names contain only lowercase ASCII letters and
   digits, and are at most 58 bytes before the file extension.

The digest distinguishes case, punctuation, accents, whitespace, non-Latin names,
and characters beyond the truncated prefix. Thus B.o.B and BOB differ even on a
case-insensitive filesystem. Canonically equivalent Unicode spellings deliberately
share a name. Blank input and invalid Unicode surrogate data are rejected.

The fixed prefix and digest avoid Windows reserved device names. Separators,
control characters, spaces, punctuation, and trailing dots cannot enter output.
File extensions such as .mp3 are appended by the storage layer, not by this API.
See [Microsoft filename rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file).

This is collision-resistant, not a mathematical uniqueness guarantee: the suffix
has 128 bits, and identical text intentionally produces identical names. Storage
must still track ownership and refuse conflicting writes. Distinct USDB entries
with identical titles need their Song IDs incorporated by the storage layout.
The module does not infer that different spellings identify the same artist.

Component limits do not guarantee full-path limits. Storage must account for the
configured root, nested folders, extension, OS configuration, and filesystem.
This module is not a complete path security or overwrite policy.

Original SongEntry/TXT metadata remains unchanged. Name changes after a future
algorithm revision will need a migration plan once a real library exists; the
fixed-vector test detects accidental drift. This initial policy is reviewable,
not a product requirement to expose hashes to users in the UI.
