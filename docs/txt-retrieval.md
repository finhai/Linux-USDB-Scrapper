# TXT retrieval (card 23)

The authenticated probe for song 3289 reported a POST gettxt form with a hidden
wd field, a time assignment of 24, a 1000 ms timer and form submission. The client
preserves the hidden field, waits the count plus one terminal tick, and POSTs once
to the same song on HTTPS USDB. Unknown forms/timers fail without submission.
No page JavaScript runs. No repeated retries or browser automation are used.

TxtClient.retrieve_page returns the final response HTML, not a parsed song.
Content extraction and legacy encoding support belong to card 24. The countdown
interpretation is conservative and passed live end-to-end verification for song 3289.
Run scripts/check_usdb_txt.py in a terminal; credentials remain in memory and
only textarea counts and boolean content markers are printed. No raw page,
lyrics, wd value, password or cookie is logged. Call the client from a worker.

Status: 249 offline tests and quality/build checks pass. On 2026-10-20 the user
ran scripts/check_usdb_txt.py against live USDB: follow_up_completed=true,
textarea_count=1, and title, artist, note and end markers were all present.
This verifies the HTTP wait/POST retrieval sequence for that song. It does not
verify legacy encoding fidelity or full TXT model parsing (subsequent cards).
The desktop interface is not wired to this client.
