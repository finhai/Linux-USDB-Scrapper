# Download queue (card 29)

DownloadQueue(worker, limit=2) owns FIFO scheduling on one asyncio event loop.
Create it within that loop, enqueue QUEUED DownloadItems, and inspect immutable
snapshots. Each song ID may be submitted once per queue. Completed/failed
snapshots remain available. Retry and cancellation are subsequent work.

The worker receives a DOWNLOADING snapshot and returns only once the complete
bundle has succeeded. Exceptions mark it FAILED with a generic message, then
release capacity for the next item. A successful return marks it COMPLETED;
actual four-file verification belongs to the worker, not this scheduler.

set_limit changes the active limit. Increasing starts waiting work immediately.
Decreasing does not cancel running jobs: their count can temporarily exceed the
new limit, but no additional job starts until a slot becomes available.
wait_idle waits for all accepted work; close rejects new jobs and drains it.
The owner must await close before shutting down its loop. Blocking network work
must be adapted off-loop; this component does not create a Qt/asyncio bridge.

The DownloadItem/DownloadBundle implementation and tests were brought forward
from feat/11-download-item-model because that pending dependency was absent from
this chain. The four fixed file extensions remain that model's existing policy.

Validation: event-gated tests verify five jobs with a limit of two, FIFO starts,
live limit increases/decreases, failure capacity release, immutable snapshots,
invalid configuration, duplicate rejection and clean draining. No credentials or
network requests are needed. GUI controls and real bundle downloads are pending.
