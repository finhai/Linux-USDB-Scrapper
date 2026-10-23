# TXT extraction and decoding (card 24)

TxtClient.retrieve_text(song_id) performs the verified wait/POST sequence and
returns the single textarea payload as Unicode text. It does not parse song
metadata, rewrite filenames, or modify note lines. HTML entities are decoded
once; literal markup is preserved. Line endings follow HTML textarea behavior.
Missing, empty, incomplete or multiple textareas raise ContentDecodeError.

Response bytes are decoded before authentication checks and extraction. BOMs
win, followed by the HTTP charset, then an HTML charset declaration. With no
declaration, strict UTF-8 is tried before Windows-1252. Latin-1/ASCII HTML labels
use the Windows-1252 mapping. Invalid or unsupported declared encodings raise a
sanitized error rather than silently replacing characters. This fallback cannot
identify every undeclared legacy encoding, or repair already-corrupted source
text. Such cases need explicit evidence before adding another encoding policy.

Offline fixtures cover accents, euro signs, smart quotes, Japanese UTF-8,
UTF-16 BOMs, HTML entities, literal tags, malformed payloads and invalid bytes.
Live card-23 retrieval succeeded; card-24 acceptance still needs a human
comparison of special characters against the website. No claim of universal
encoding detection or live special-character fidelity is made.

On 2026-10-20 the user ran the updated production check for song 3289:
follow-up and production extraction completed, no U+FFFD replacement character
was present, and title, artist, note and end markers were all found. This
confirms live extraction but does not establish special-character fidelity;
that human comparison remains pending.
