# Combined search and sort investigation — card 18

Known from the board: the listing endpoint accepts POST fields `interpret`
(artist), `title`, and `details=1`. The observations below verify combined filtering for one example and ID sort
direction. Other sort fields are discovered but not empirically checked.

Run `scripts/probe_usdb_search.py` locally with hidden credential prompts. It uses
the verified session client, keeps cookies in memory, and emits a JSON summary.
No raw HTML, credentials, hidden input values, or cookies are saved or printed.

The probe compares ABBA-only, Dancing Queen-only, both together, and the same title
with a deliberately unmatched artist. It also compares Don't Stop, Dont Stop,
dont stop, and Dónt Stóp for the deferred normalization investigation (card 12).
Requests are sequential and spaced one second apart.

These are first-page candidate IDs from same-origin `link=detail&id=...` links,
not a production result parser or total counts. Widgets may also contain detail
links. An empty list can mean a changed layout. Pagination, result-row scope and
sort behavior must be verified before claiming equivalence or combined filtering.

The summary reports field names, sort-related link parameters and select option
values. It does not execute unknown controls or fetch arbitrary links. Once the
actual controls are known, validate ascending/descending order against result rows.
The requested UI state rule is settled: selecting a new field starts ascending;
selecting the same field again toggles direction.

Status: two authenticated probe runs recorded below; search request API and sort
state implemented. Parsing, pagination and GUI work remain separate. This branch depends only on session-client
PR #8, not the later expiry/retry branches. Its smaller test count reflects that
branch base, not removal of tests. CI requires retargeting to dev after #8 merges.

## First authenticated observation — 2026-10-19

The maintainer reported 30 artist-only candidates, six title-only candidates,
combined ABBA + Dancing Queen candidate 3289, and zero candidates for a deliberately
unmatched artist. This supports combined filtering for that example; it does not
prove the parser scopes only result rows or prove complete pagination.

Observed order values: id, interpret, title, genre, year, edition, golden,
language, autor, rating, views, lastchange. A separate ud control is present,
but its values were omitted by the first probe's discovery filter.

All four normalization searches yielded zero candidates. These ran after the
unmatched artist search and omitted interpret, so retained server-side filters
are a possible confounder. They do NOT establish normalization equivalence.

The corrected probe sends both artist and title explicitly (empty when unused),
resets start to zero, reports echoed filter values, captures ud controls and tests
up to two discovered direction values using order=id. It includes a title-only
positive control after the negative case. It reports numeric candidate order;
result-row scoping remains a limitation. No guessed direction values are sent.

## Corrected authenticated observation — 2026-10-19

With explicit artist/title fields, combined ABBA + Dancing Queen again returned
3289 and the unmatched artist returned no candidates. The positive title-only
control after the negative returned six candidates, as before. Echoed input values
were always empty, including successful queries, so they cannot prove filter state.

The discovered ud options are asc and desc. With order=id and title=Dancing Queen:
asc returned [876, 3289, 4609, 9328, 13620, 23827]; desc returned exactly the reverse.
This verifies direction for ID sorting on this sample. Other sort fields were
observed in controls but their collation and tie-breaking are not yet verified.
The four normalization variants still yielded no candidates; this is not evidence
that removing punctuation/accents is safe. Card 12 remains unverified.

## Search API

SearchClient(session).search_html(SearchQuery(artist="ABBA", title="Dancing Queen"))
posts both filters with details=1, start=0, order=id and ud=asc by default. Text is
preserved exactly; no unverified normalization is applied. SortState.select(field)
returns a new state: first selection ascending, repeat toggles, new field ascending.
All observed sort fields are enumerated, including creator mapped to autor.

The API returns first-page HTML in server order. It does not yet parse SongEntry
records, paginate, or expose GUI controls; those remain subsequent cards. Never
log the returned HTML. Automated tests cover request construction and state changes;
the user's probe establishes the underlying live protocol, not an end-to-end GUI test.
