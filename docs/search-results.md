# Deduplication by Song ID — card 21

merge_song_results(*sources) combines iterables of SongEntry into an immutable
tuple. Sources are consumed in order; the first occurrence of each USDB Song ID
is kept intact, in encounter order. Artist/title text never determines identity.
Two identical titles with different IDs remain separate. Inputs are not modified.

When records with the same ID disagree, the first source wins. This deliberately
does not merge individual metadata fields: callers choose source priority and
perform enrichment separately. Entries without YouTube URLs are retained. The
final video filter belongs to card 22, after enrichment and deduplication.

Generators are supported and consumed once. An invalid record or source failure
raises rather than returning a partial result. Memory scales with unique IDs.
This is an in-memory union, not a global sort across independently sorted searches;
a later presentation layer must define any combined ordering requirement.

Offline acceptance verifies overlapping artist/title search results produce the
shared ID exactly once, including differing metadata, identical text under distinct
IDs, repeated records, empty sources, generators and failures. No live HTTP behavior
is needed for this deterministic identity rule. Pipeline wiring remains card 22.

This branch starts directly from dev and does not depend on the other client PRs.
