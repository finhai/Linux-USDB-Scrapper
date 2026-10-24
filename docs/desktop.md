# Desktop workflow

The app opens on a login page. Users can choose “Remember me for 30 days”.
Credentials and their original save time are stored only in the native keyring.
A valid saved login is verified before opening the main interface. Its expiry
is fixed: automatic login never extends it. Expired entries, old entries without
a timestamp, unavailable keyrings, and failed authentication return to the login
page. Without Remember me, credentials remain in memory for this run only.

Search loads 100 source rows at a time, enriches details with one-second spacing,
and displays only rows with supported YouTube links. Scrolling to the bottom
loads the next page; Load more is available too. Changing the sort field resets
to ascending; selecting the same field toggles. Searching/enrichment runs in
background workers and may take over a minute for a full source page.

Selected results are added to a waiting queue without starting transfers. Press
Start queued downloads in the Downloads tab to start the current batch. Later
additions wait for another press. Retry returns failed/cancelled items to the queue. The Downloads tab displays actual
queue states and the current bundle stage, with cancellation/retry controls.
No byte-percentage estimate is shown. Settings apply concurrency immediately;
a new root applies to newly queued jobs. Settings persist atomically, without
passwords. Forget credentials removes the native keyring entry.

Closing cancels background operations and waits for blocking HTTP work to stop
before removing staged files. HTTP calls have bounded timeouts. Views import
backend operations only through the controller; an AST test enforces this.

Offline integration drives real Qt views and the controller through startup
login, search, enqueue, complete bundle, settings save and shutdown. External
services and media are synthetic in that test. Live desktop end-to-end acceptance,
media playback, and clean-machine platform checks remain pending.


The interface uses a dark purple palette, violet actions, teal start controls and
colored states. Search and Downloads show USDB cover thumbnails. The controller
loads JPEGs in background and keeps a bounded 32 MB cache; downloads reuse cached
image bytes when available and otherwise use the same USDB endpoint. Unavailable
covers have a placeholder and do not block selecting the song.

New library paths preserve readable artist/title spelling and Unicode. A song
folder uses only the title; TXT/MP3/MP4/JPG use the title
as their common filename stem, and TXT media headers match those filenames.
Unsafe filesystem characters and overly long names are sanitized with a short
collision suffix only when needed. Existing hashed folders are not migrated.
