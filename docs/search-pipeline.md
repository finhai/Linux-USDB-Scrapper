# Search pipeline — card 22

```python
from usdb_scrapper.usdb_client import (
    DetailClient,
    PagedSearchClient,
    SearchPipeline,
    SearchQuery,
    UsdbSession,
)

with UsdbSession() as session:
    session.login(username, password)
    pipeline = SearchPipeline(PagedSearchClient(session), DetailClient(session))
    stages = pipeline.run(SearchQuery(artist="ABBA", title="Dancing Queen"))
    songs_with_video = stages.output
```

The stages are deliberately separate and available for inspection:

1. retrieved: complete pagination for every supplied query; no filtering or dedup.
2. enriched: every occurrence retained, with a detail-derived video URL or None.
3. deduplicated: first record per Song ID, preserving source/encounter order.
4. output: only records with supported YouTube video references.

retrieve, enrich, merge_song_results and filter_video_results can be tested and
used independently. All snapshots are tuples of immutable SongEntry records.
Details are fetched once per unique ID per run and reused across duplicate records,
without discarding those records before the dedup stage. The cache does not persist
between runs. Detail lookups and separate query requests are spaced one second apart.
The paginator also spaces its own pages. Run in a worker, never on the GUI thread.

Multiple video candidates use the first supported reference in comment encounter
order, normalized to a canonical watch URL. This deterministic policy does not
establish relevance, video availability or downloader compatibility. The detail API
still exposes all candidates for future selection UI. No early filter uses the
unresolved youtube_url from a listing record. Detail/page failures propagate; they
are never treated as video absence or silently returned as partial success.

Source order is preserved across queries, not globally re-sorted. Caller-supplied
max_pages bounds each query. Empty input returns empty stages without HTTP calls.
Large searches can require many detail requests; no background execution or GUI
progress/cancellation is added in this card.

Validation covers stage snapshots, overlapping paths, one lookup per ID, failures,
wrong detail IDs, unsupported candidates, empty input, and real paginator/parser
composition over synthetic HTTP responses. No live end-to-end pipeline run is claimed.

This branch combines the exact deduplication files from PR #14 with the client
chain through PR #13. Both prerequisites must be integrated before retargeting
to dev and running CI. There are no dependency changes.
