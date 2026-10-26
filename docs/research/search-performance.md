# Search release improvements — 2026-10-25

Previously, the desktop waited for every result's detail page and a one-second
pause per song before emitting the first rows. A full page therefore incurred
at least 100 seconds of deliberate delay, plus HTTP time. It also removed songs
without a YouTube URL in comments, although TXT metadata can supply a source.

The desktop now emits the listing directly, then checks comments and fetches
covers separately. Hints never claim media playability or hide results. The
standalone historical SearchPipeline API remains separate from this desktop flow.

Authenticated live check, using the production Gateway and title “Love”:
- First 100 rows: 0.53 seconds, more pages available.
- Next 100 rows: 0.31 seconds, more pages available.
- No shared IDs between the two pages.

These are two observations on one connection, not a speed guarantee. No live
before/after timing of the old full detail-enrichment path was performed; its
100-second lower bound follows from the code's explicit pauses.

Offline tests exercise results appearing while source checks are blocked,
cache hits and Refresh, fixed cache expiry and capacity, failed-page retry
without offset advancement, cancellation and suppression of stale rows.
Caches hold only parsed metadata in memory and expire after 15 minutes.
