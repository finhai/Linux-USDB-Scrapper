# Pagination and result rows — card 19

## Live protocol evidence (2026-10-19)

The maintainer ran the discovery probe with title=Love and ascending ID sort.
start=0/limit=100 returned 100 candidate rows, start=100/limit=100 returned another
100, and start=90/limit=30 exactly matched the last ten of the first page followed
by the first twenty of the second. Both full pages had unique, disjoint IDs.
This verifies offsets and page sizes at that boundary on the observed site.

Sample result rows have 13 cells: selection, image, artist, title/detail link,
genre, year, edition, golden notes (Yes/No), language, creator, rating images,
views, and an image/action cell. No raw authenticated pages or credentials saved.

## Implementation

parse_listing validates the observed detailed-listing controls and 13-cell rows,
requires one positive song ID in the title column, and produces immutable SongEntry
records. Blank optional text becomes None. Year/views must be numeric; golden notes
must be Yes/No/blank. HTML entities are decoded and display whitespace collapsed.
Image-only rating and unavailable dates/YouTube links remain None. They are not
inferred from image counts. A future layout or unexpected metadata raises
ListingParseError rather than dropping records. A recognized listing with no detail
links is empty; unrecognized responses or unaccounted detail links are rejected.

PagedSearchClient.search preserves explicit query fields and server sort order,
requests limit=100 with offsets 0,100,..., and pauses one second between requests.
A short page terminates traversal; an exact multiple needs an extra empty page.
It collects all records before returning, detects duplicate rows/page overlap,
and raises if max_pages is exhausted rather than presenting truncated success.
Default bound is 100 pages. HTTP/authentication errors propagate. Call in a worker.

The server offers no snapshot guarantee: concurrent catalogue changes or unstable
sort ties may still cause omissions. Overlap is detected, but a complete snapshot
cannot be guaranteed by offset pagination alone. ID sorting is the verified default.

## Validation

200 offline tests pass on this branch, including >100 records, exact page multiples,
malformed rows, overlaps, page bounds and later-page failures. The live discovery
boundary passed. The maintainer also ran the production parser/paginator on
2026-10-19: it completed with 1,024 records, unique IDs in ascending order, and
artist/title present on every record. First IDs: 9, 37, 50, 88, 148. Last IDs:
32313, 32388, 32417, 32480, 32485. This validates the tested search across 11 pages.
No credentials, cookies or raw pages were retained. To repeat the check:

```sh
cd /home/faule/MySoftware/Linux-USDB-Scrapper && .venv/bin/python scripts/check_usdb_pagination.py
```

This performs the full Love search with a 50-page bound and outputs only summary
counts and boundary IDs. Card 19 remains open until acceptance, CI and merge.
This branch depends on PR #11; reconcile/retarget to dev after prerequisite merge.
