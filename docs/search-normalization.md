# Search normalization (card 12)

The pure `normalize_search_input` function is exported from
`usdb_scrapper.normalization.search`. It has no network, client, domain, or
filesystem-normalization dependencies. Apply it to user queries, never to stored
artist/title metadata or filenames.

Defaults perform NFC Unicode composition, trim outer whitespace, and collapse
Unicode whitespace runs to one space. Case, accents, and punctuation stay intact.
No policy is yet certified as matching USDB's search semantics.

SearchNormalizationPolicy exposes independent, explicit options:

- casefold: Unicode case folding, off by default (Straße becomes strasse).
- strip_diacritics: remove Unicode mark characters after NFD decomposition,
  off by default. This is lossy across scripts; it is not general transliteration
  (ø and ł remain unchanged). Do not enable globally without live evidence.
- punctuation: PRESERVE (default), REMOVE, or SPACE. Uses Unicode punctuation
  categories, not all symbols: plus signs remain symbols. REMOVE joins text
  (AC/DC → ACDC); SPACE separates it (AC/DC → AC DC).

The result is recomposed to NFC and whitespace normalized. Empty/whitespace-only
input produces an empty string; punctuation removal may also produce empty text.
The future controller must decide whether such queries are allowed. The function
returns plain text, not URL-encoded data; the HTTP client owns request encoding.

With all lossy options enabled and punctuation REMOVE, Don't Stop, Dont Stop,
dont stop, and Dónt Stóp produce `dont stop`. Unit tests prove that mapping only;
they do not prove those variants return the same songs on USDB.

## Live investigation: still required

On 2026-10-18, unauthenticated read-only search POSTs to
https://usdb.animux.de/?link=list with fields title and details=1 were made for
the four examples above. Every response required login instead of providing
search results. No credentials or cookies were supplied or saved. HTTP success
and a search-page title are not evidence of a successful search.

After authentication is available, compare Song ID sets and total counts for
original and transformed queries, including pagination. Test punctuation,
accents, case, word separators, and multiple scripts independently. Choose the
least destructive policy that preserves intended matches, record the evidence,
and update the default only when justified. Live failures or login pages must
never be recorded as empty search results.

Card 12 remains incomplete until this empirical decision is made. The draft PR
provides the pure module and offline tests, not a verified production search
policy. No automated network checks are included in the unit suite.
