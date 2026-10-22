# Desktop workflow

Search, Downloads and Settings now connect to an application controller. The app
opens without a login prompt. Search uses remembered native-keyring credentials
when available, otherwise opens the login dialog. Credentials remain in memory
for the session; keyring failures permit session-only use.

Search loads 100 source rows at a time, enriches details with one-second spacing,
and displays only rows with supported YouTube links. Scrolling to the bottom
loads the next page; Load more is available too. Changing the sort field resets
to ascending; selecting the same field toggles. Searching/enrichment runs in
background workers and may take over a minute for a full source page.

Selected results enqueue four-file downloads. The Downloads tab displays actual
queue states and the current bundle stage, with cancellation/retry controls.
No byte-percentage estimate is shown. Settings apply concurrency immediately;
a new root applies to newly queued jobs. Settings persist atomically, without
passwords. Forget credentials removes the native keyring entry.

Closing cancels background operations and waits for blocking HTTP work to stop
before removing staged files. HTTP calls have bounded timeouts. Views import
backend operations only through the controller; an AST test enforces this.

Offline integration drives real Qt views and the controller through deferred
login, search, enqueue, complete bundle, settings save and shutdown. External
services and media are synthetic in that test. Live desktop end-to-end acceptance,
media playback, and clean-machine platform checks remain pending.
