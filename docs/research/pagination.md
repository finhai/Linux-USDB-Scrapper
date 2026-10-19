# Pagination and result-row discovery — card 19

The search protocol exposes start and limit controls. Their offset semantics,
100-result page size and result-row structure still need authenticated evidence.
The production search API currently returns only first-page HTML.

Run scripts/probe_usdb_pagination.py locally with hidden credential prompts. It
searches for Love in ascending ID order with these proposed page parameters:
start=0/limit=100, start=100/limit=100, and start=90/limit=30. These are hypotheses
to test, not settled protocol facts. The boundary page should equal the last ten
IDs of the first page plus the first twenty IDs of the second page.

The JSON reports candidate leaf-table-row IDs, duplicate indicators, two sample
song rows per page, sort-header cell positions, and numeric pagination controls.
Nested layout rows are excluded. Inputs, scripts, raw HTML, cookies and image URLs
are not emitted; only sample candidate row text and visible image labels appear.
These are discovery candidates, not production SongEntry records. A changed layout
may produce empty candidates; do not interpret that as an empty search result.

Acceptance remains pending: validate the live rows and offsets, implement strict
record parsing and bounded page traversal, then prove a >100-match result has no
boundary duplication or omissions. Do not mark the card Done based on this probe.

This branch depends on PR #11. Tests currently use synthetic HTML; no live
pagination success is claimed until the maintainer supplies the JSON output.
