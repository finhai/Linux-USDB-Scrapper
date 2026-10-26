# Song Entry contract

`from usdb_scrapper.domain import SongEntry` is the public API for card 9.
The standard-library dataclass is frozen, slotted, and keyword-only. It has no
USDB client, Qt, filesystem, or network dependency and does not extract page data.

Required fields: `song_id` (positive integer), `artist` and `title` (nonblank text).
Original text, including punctuation, Unicode, and surrounding spaces, is retained.
No search or filesystem normalization occurs here.

Optional fields default to `None`: `youtube_url`, `date`, `genre`, `year`,
`edition`, `golden_notes`, `language`, `creator`, `rating`, `views`, `last_modified`.
Unknown values remain distinct from zero views/rating and false golden notes.
Dates are Python `datetime.date` values, not strings or datetimes. Year is 1–9999;
views are nonnegative integers. Rating must be finite and nonnegative; no maximum
or rating scale is invented before the client investigation. Optional text must
be nonblank when supplied; upstream extraction should map missing text to None.

YouTube URL validation checks HTTP(S), exact supported hosts (youtube.com,
www.youtube.com, m.youtube.com, youtu.be), a nonempty path, and absence of
credentials, explicit ports, whitespace, or control characters. It preserves the
supplied link; it does not extract video IDs, certify a video URL's playability,
resolve links, or perform the later pipeline's usable-video filtering. Those
are separate concerns. A link may remain None before enrichment or when absent.

Wrong types raise TypeError; out-of-range or malformed values raise ValueError.
No automatic coercion occurs (including booleans masquerading as integers).
Future client adapters must translate source formats into this contract. Date
precision and rating scale should be revisited if verified source data requires it.

Use `song_id` explicitly as the deduplication key. Dataclass equality compares the
entire snapshot; it does not discard changes to metadata for the same song.
Use `dataclasses.replace(entry, youtube_url=...)` for enrichment: the original
remains unchanged and validation runs again. Actual deduplication is card 21.
