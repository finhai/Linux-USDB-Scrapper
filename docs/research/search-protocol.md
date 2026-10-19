# Combined search and sort investigation — card 18

Known from the board: the listing endpoint accepts POST fields `interpret`
(artist), `title`, and `details=1`. Their combined semantics and actual sort
parameters remain unverified. Do not implement guessed server parameters.

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

Status: probe and synthetic extraction tests prepared; authenticated evidence
pending. Card 18 remains WorkingOn. This branch depends only on session-client
PR #8, not the later expiry/retry branches. Its smaller test count reflects that
branch base, not removal of tests. CI requires retargeting to dev after #8 merges.
