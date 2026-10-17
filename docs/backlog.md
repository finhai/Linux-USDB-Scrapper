# Trello snapshot

Read on 2026-10-18. Trello remains the planning source of truth. This snapshot does not mark cards complete.

## Planned

### [Reproducible dev environment & dependency management](https://trello.com/c/Lc6cJrYo/6-reproducible-dev-environment-dependency-management)

Establish a reproducible development environment: a pinned language version, a single documented command that takes a fresh clone to a working dev setup, and a locked dependency file so builds are repeatable.

Acceptance: a fresh clone can go from zero to a running dev environment with one documented command.

Note: this is the one setup item where naming a concrete tool is genuinely unavoidable to call it "complete." Flag here if you want a specific one named now — otherwise it gets picked when this card is actually worked.

[Phase 1 — Environment & Project Setup]

### [Test runner & baseline check](https://trello.com/c/T3twwMMu/7-test-runner-baseline-check)

Set up a test runner with a single command to run the full suite, plus a minimal static-analysis/lint check.

Acceptance: a trivial test exists and passes, proving the harness itself works, before any real component depends on it.

[Phase 1 — Environment & Project Setup]

### [Logging & error-handling convention](https://trello.com/c/y2IimTBU/8-logging-error-handling-convention)

Decide and document the project's logging and error-handling convention before any other phase writes code against it: what gets logged where, how errors propagate between layers (e.g. does the USDB Client raise typed exceptions the Controller layer catches, or return result objects?), and what the frontend does with a failure it can't resolve itself.

Acceptance: a short written convention exists that every phase from here on can be held to, not invented ad hoc per component.

[Phase 1 — Environment & Project Setup]

### [Song Entry domain model](https://trello.com/c/vy0IkCek/9-song-entry-domain-model)

Define the Song Entry model: the shape every USDB search result gets normalized into before it reaches anything else in the app.

Fields: USDB Song ID (the stable unique identifier), Artist, Title, YouTube link (resolved via the entry-page comments per the research), plus whatever sort/display metadata the search results already expose (date, genre, year, edition, golden notes, language, creator, rating, views, last modified).

Acceptance: pure data + validation only — no network calls, no parsing logic, nothing that reaches into the USDB Client. Every later phase (search, filtering, dedup, the frontend) depends on this shape without needing to know how it was produced.

[Phase 2 — Core Domain Models]

### [UltraStar TXT in-memory model](https://trello.com/c/Hqz5m29z/10-ultrastar-txt-in-memory-model)

Define the in-memory representation of a parsed UltraStar TXT file.

Fields to track: VERSION, TITLE, ARTIST, AUDIO, BPM (mandatory per spec), VIDEO and COVER (spec-optional but required for this app), GENRE (genuinely optional) — plus the note/phrase block, preserved as an opaque, untouched block that nothing outside the Parser interprets or reformats.

Acceptance: the model can represent a file missing GENRE without breaking. It has no built-in awareness of legacy-input quirks (`#MP3` fallback, the YouTube meta-tag syntax) — that translation is the Parser's job (a later phase), not this model's.

[Phase 2 — Core Domain Models]

### [Download Item domain model](https://trello.com/c/HnrOf4N5/11-download-item-domain-model)

Define the Download Item model: the unit of work the Download Manager (a later phase) queues and tracks.

Fields: the target four-file bundle (txt/mp3/mp4/jpg) for one Song Entry, plus state — QUEUED → DOWNLOADING → COMPLETED, or DOWNLOADING → FAILED → RETRY.

Acceptance: pure data + a state machine only — no actual downloading, no filesystem access, no YouTube-specific logic. The Download Manager phase depends on this shape; this model doesn't depend on it back.

[Phase 2 — Core Domain Models]

### [Search-input normalization module](https://trello.com/c/6HG1Wcou/12-search-input-normalization-module)

Build the normalization pipeline applied to user search input before it's sent to USDB: case folding, diacritic handling, punctuation/whitespace handling — exact aggressiveness determined empirically against real USDB search behavior (flagged in the research doc as needing a proof-of-concept, not yet resolved). Lives entirely separate from filesystem normalization — the two must never share code or assumptions, since "searchable" and "filesystem-safe" are different problems.

Acceptance: a pure function/class, no network dependency, testable with input→expected-output pairs including the cases from the research (Don't Stop / Dont Stop / dont stop / Dónt Stóp).

[Phase 3 — Normalization & Sanitization]

### [Filesystem-name normalization module](https://trello.com/c/TVthCfHn/13-filesystem-name-normalization-module)

Build the deterministic, collision-aware normalization pipeline that turns Artist/Title into safe local directory and file names: no spaces, no punctuation, no characters unsafe on either target platform. Lives entirely separate from search-input normalization — this module never touches network code or the GUI. The original Artist/Title values are never destroyed by this — they stay intact in the TXT and the Song Entry; only the filesystem path is normalized.

Acceptance: a pure function/class, deterministic (same input always produces the same output), testable against the collision-risk cases already identified (e.g. "B.o.B" vs "BOB").

[Phase 3 — Normalization & Sanitization]

### [Prove out USDB login mechanics (spike)](https://trello.com/c/Wx1cyoUj/14-prove-out-usdb-login-mechanics-spike)

Highest-risk open item in the whole project. Determine, against the real site, whether a plain credential POST yields a working authenticated session, or whether the cookie-extraction-from-browser workaround found in prior art is actually necessary. This is explicitly a throwaway investigation, not production code — its only job is to answer the question and inform how the session client gets built.

Acceptance: a written answer (which mechanism actually works), not shippable code.

---
Findings so far (logged-in page capture, 2026-08-01): the homepage embeds a Matomo analytics call — `_paq.push(['setUserId', 'Faule'])` — with the username hardcoded server-side into the HTML. Strong signal this is a conventional server-side session (PHP-style session cookie), not a token/header scheme — suggests a plain HTTP client with a cookie jar is likely sufficient, though this isn't proof yet. Still needed: the actual login page/form source (field names, any CSRF token, any client-side challenge), and ideally a captured login request/response showing the `Set-Cookie` header directly.

---
Update (network capture, 2026-08-01): confirmed directly from real request headers — the session cookie is named exactly `PHPSESSID`, PHP's own default. No custom cookie name, no additional auth header or bearer token anywhere across a full page load — everything rides on that one cookie. The other cookies present (`ziparchiv`, `counter`, both empty; two Matomo analytics cookies) are unrelated to login. Still open: this capture is mid-session, not the login POST itself, so the `Set-Cookie` response and the actual field names on the login form remain unseen. The capture that would close this card out: log out, view the resulting login form, log back in with the network tab recording, and save that — the request body (field names) plus the `Set-Cookie` header on the response would settle this definitively.

[Phase 4 — USDB Client: Authentication & Session]

### [Authenticated session client](https://trello.com/c/jhML5y5B/15-authenticated-session-client)

Build the client that logs in and holds an authenticated session for subsequent requests, using whichever mechanism the login-mechanics spike validated.

Acceptance: can log in with valid credentials and make at least one authenticated request afterward, against the real site.

[Phase 4 — USDB Client: Authentication & Session]

### [Session-expiry / invalid-session detection](https://trello.com/c/ZKhvBYym/16-session-expiry-invalid-session-detection)

Detect when a session has expired, been invalidated, or when a request unexpectedly lands on a login page instead of the expected content.

Acceptance: a request made with a deliberately invalid/expired session is correctly identified as such, rather than being misread as a different kind of failure or, worse, silently succeeding with wrong data.

[Phase 4 — USDB Client: Authentication & Session]

### [Automatic re-authentication & retry](https://trello.com/c/H87y6kOb/17-automatic-re-authentication-retry)

When an operation fails due to an expired/invalid session and stored credentials are available (via the Credential Manager), re-authenticate automatically and retry the original operation once.

Acceptance: a request that fails due to session expiry succeeds transparently on retry, without the caller needing to know a re-auth happened.

[Phase 4 — USDB Client: Authentication & Session]

### [Combined Artist+Title search with sort control](https://trello.com/c/QhornbZY/18-combined-artisttitle-search-with-sort-control)

Implement search against USDB's listing endpoint, accepting Artist and Title together, with the single sort control (field + direction) behaving as specified: first selection sorts ascending, reselecting the same field toggles direction, switching fields resets to ascending.

Acceptance: a search returns results in the order the sort control specifies, verified against the real site.

---
Confirmed (logged-in page capture, 2026-08-01): search happens via POST to `?link=list`. The site's own quick-search links use two separate forms — one posting `interpret` (artist) alone, one posting `title` alone, both with a `details=1` hidden field. Field names are now settled fact. Not yet confirmed whether both fields can be posted together in one request for a true combined search — worth testing directly before assuming it works.

[Phase 5 — USDB Client: Search & Entry Retrieval]

### [Server-side pagination](https://trello.com/c/DqmSeXvi/19-server-side-pagination)

Implement pagination against USDB at 100 results per request, producing Song Entry records.

Acceptance: a search spanning more than 100 matches correctly retrieves subsequent pages without duplicating or dropping entries.

[Phase 5 — USDB Client: Search & Entry Retrieval]

### [Entry-page fetch: YouTube link + cover](https://trello.com/c/goosZavG/20-entry-page-fetch-youtube-link-cover)

For a candidate Song Entry, fetch its entry/detail page and extract the YouTube link from the comments.

Acceptance: given a real Song ID, returns the YouTube URL if present, or clearly indicates it's absent rather than failing silently.

---
Update (logged-in page capture, 2026-08-01): cover art does NOT need this fetch at all — cover images follow a direct, predictable URL: `data/cover/<song id>.jpg`. This card's scope narrows to YouTube-link extraction only; cover retrieval is now independent, keyed on Song ID alone, and can't fail just because a comment-parsing pass fails.

Also found: real comments carry YouTube references in two different formats — a bare URL and a `[youtube]URL[/youtube]` BBCode-style tag. Seen so far only in a homepage preview widget that appears to show raw, unrendered comment text — needs confirming against an actual song detail page, where BBCode may render differently (e.g. as a real link or an embedded player).

[Phase 5 — USDB Client: Search & Entry Retrieval]

### [Deduplication by Song ID](https://trello.com/c/qeu6D9kM/21-deduplication-by-song-id)

When Artist and Title searches produce overlapping results, deduplicate using the USDB Song ID as the canonical key — not Artist+Title text matching.

Acceptance: a search producing the same Song ID via two different query paths surfaces that entry exactly once.

[Phase 5 — USDB Client: Search & Entry Retrieval]

### [YouTube-link filter as final pipeline step](https://trello.com/c/1Il3GzN6/22-youtube-link-filter-as-final-pipeline-step)

Wire the full search pipeline so entries without a usable YouTube link are dropped only as the last step — after pagination, entry-page fetch, and dedup — never earlier.

Acceptance: the pipeline's intermediate stages can be tested independently of the filter; only the final output is YouTube-link-filtered.

[Phase 5 — USDB Client: Search & Entry Retrieval]

### [TXT wait-page handling](https://trello.com/c/ylqmy0B7/23-txt-wait-page-handling)

Implement the request sequence for retrieving a TXT file: detect the wait-page, wait the required interval, submit the follow-up request, and confirm plain HTTP handling is sufficient (per the research, this looks avoidable without a full browser-automation engine, but hasn't been proven with working code yet).

Acceptance: a real TXT file is retrieved end-to-end against the live site without browser automation.

[Phase 6 — USDB Client: TXT Retrieval]

### [TXT content extraction & decoding](https://trello.com/c/muWO6DV5/24-txt-content-extraction-decoding)

Extract the TXT payload from the response, decode HTML entities correctly, and determine the correct text encoding, tolerating legacy encodings that may appear in older files.

Acceptance: a retrieved file's content matches what a human would see, including any special characters, with no mojibake. Hands the raw text straight to the Parser — no interpretation happens here.

[Phase 6 — USDB Client: TXT Retrieval]

### [TXT parsing into the domain model](https://trello.com/c/PYbWkGHD/25-txt-parsing-into-the-domain-model)

Parse raw TXT content into the UltraStar TXT in-memory model, tolerating legacy input (`#MP3` instead of `#AUDIO`, the YouTube meta-tag syntax inside `#VIDEO`) without those specifics leaking into the model itself.

Acceptance: a real file using `#MP3` and the `v=<id>` meta-tag convention parses correctly into the same shape as a file already using `#AUDIO` and a literal path.

[Phase 7 — UltraStar Parser/Editor]

### [Metadata rewriting to local paths](https://trello.com/c/0b6NbCN6/26-metadata-rewriting-to-local-paths)

Rewrite VIDEO, AUDIO, and COVER fields to point at the local files once downloaded, never emitting a YouTube reference or the meta-tag syntax in the output.

Acceptance: serialized output never contains a YouTube ID/URL anywhere, under any input condition.

[Phase 7 — UltraStar Parser/Editor]

### [Spec-valid TXT serialization](https://trello.com/c/EMQEwXIh/27-spec-valid-txt-serialization)

Serialize the in-memory model back to a TXT file that satisfies the official spec (UTF-8 without BOM, `#AUDIO` not `#MP3`, required fields present), with the note/phrase block preserved exactly as parsed.

Acceptance: output validates against the spec's required-field list.

[Phase 7 — UltraStar Parser/Editor]

### [Round-trip fidelity test](https://trello.com/c/dSjz3oIN/28-round-trip-fidelity-test)

Prove parse → modify → serialize → re-parse is lossless for anything not intentionally changed — especially the note/phrase block, which must never be touched by anything outside this component.

Acceptance: a real file, round-tripped with only VIDEO/AUDIO/COVER changed, is byte-identical elsewhere to the original.

[Phase 7 — UltraStar Parser/Editor]

### [Download queue with configurable concurrency](https://trello.com/c/Ba9V2C2d/29-download-queue-with-configurable-concurrency)

Implement the queue that holds Download Items, with a user-configurable maximum number of active downloads at once.

Acceptance: queuing more items than the concurrency limit results in the excess correctly waiting, not overwhelming the limit.

[Phase 8 — Download Manager]

### [Four-file bundle download per entry](https://trello.com/c/T0aOKTWG/30-four-file-bundle-download-per-entry)

For a queued Download Item, retrieve all four files — TXT, cover, audio, video — as a single logical unit of work.

Acceptance: a completed Download Item always has all four files present together; a partially-successful entry is identifiable as such, not silently treated as done.

[Phase 8 — Download Manager]

### [Progress, cancellation, retry](https://trello.com/c/ZgXoNcLs/31-progress-cancellation-retry)

Report per-item download progress, support cancelling an in-progress or queued item, and support retrying a failed one.

Acceptance: cancelling an active download stops it cleanly without corrupting partial state; retrying a failed item starts cleanly from a known state.

[Phase 8 — Download Manager]

### [Partial-download handling & crash recovery](https://trello.com/c/QZfLLhq8/32-partial-download-handling-crash-recovery)

Downloads write to a non-final location until complete, so a crash mid-download never leaves a corrupt file where a finished one is expected. On restart, any leftover partial state is recognized and handled (resumed or cleanly discarded), not left as silent debris.

Acceptance: killing the process mid-download and restarting leaves the target library in a valid state, never a half-written file passed off as complete.

[Phase 8 — Download Manager]

### [Identical-skip / different-overwrite comparison](https://trello.com/c/I4lEVpgu/33-identical-skip-different-overwrite-comparison)

Before finalizing a downloaded file, compare it against any existing file at the target path: skip (and clean up) if identical, atomically replace if different — without ever removing or overwriting the existing file until the replacement has fully and successfully downloaded.

Acceptance: comparing a large file doesn't require holding two full copies in memory at once; the existing file remains valid and untouched at every point until the moment of atomic replacement.

[Phase 8 — Download Manager]

### [Isolate YouTube-downloading behind an interface](https://trello.com/c/Il326TRJ/34-isolate-youtube-downloading-behind-an-interface)

Wrap YouTube downloading behind a narrow interface the rest of the Download Manager depends on, so that this component — the single most externally volatile dependency identified in the research — can be updated or even swapped without changes rippling into queueing, progress reporting, or the rest of the bundle logic.

Acceptance: the YouTube-downloading implementation can be replaced without touching any other file in this phase.

[Phase 8 — Download Manager]

### [Artist/Song directory layout](https://trello.com/c/vb2He4Y3/35-artist-song-directory-layout)

Implement the storage layout: one directory per artist, one subdirectory per song beneath it, holding that entry's four files.

Acceptance: two different songs by the same artist land under the same artist directory; two different artists never collide.

[Phase 9 — Storage Manager]

### [Wire in filesystem normalization for naming](https://trello.com/c/yY6hNGWF/36-wire-in-filesystem-normalization-for-naming)

Use the filesystem normalization module to derive directory and file names, while keeping the original, un-normalized Artist/Title intact in the TXT's own metadata and in the Song Entry — the filesystem name and the semantic name are never the same code path.

Acceptance: an artist like AC/DC produces a safe directory name while `#ARTIST:AC/DC` still reads correctly in the TXT.

[Phase 9 — Storage Manager]

### [Configurable storage root](https://trello.com/c/1PCi7Qw4/37-configurable-storage-root)

Let the user configure where the whole library lives on disk.

Acceptance: changing the configured root does not require touching any other phase's code — the Storage Manager is the only thing that needs to know the actual path.

[Phase 9 — Storage Manager]

### [Secure credential storage, both platforms](https://trello.com/c/oZWwt6gg/38-secure-credential-storage-both-platforms)

Store and retrieve USDB credentials using native OS credential facilities on Linux and Windows — never plaintext config.

Acceptance: credentials stored, then retrieved after an application restart, on both target platforms.

[Phase 10 — Credential Manager]

### [Graceful degradation with no credential backend](https://trello.com/c/vfRTqlV6/39-graceful-degradation-with-no-credential-backend)

Handle the case where no OS credential backend is available at all (a real, documented failure mode from the research, particularly on minimal Linux setups) without crashing — fall back to prompting for credentials each session rather than failing outright.

Acceptance: the app starts and functions, minus the "remember me" convenience, on a system with no keyring backend present.

[Phase 10 — Credential Manager]

### [Wire "remember credentials" to auto re-auth](https://trello.com/c/ktaZCA3T/40-wire-remember-credentials-to-auto-re-auth)

Connect stored credentials to the automatic re-authentication flow (Phase 4), so a session expiry is resolved transparently when credentials are available, and falls back to prompting when they aren't.

Acceptance: with "remember" enabled, a session expiry recovers without user interaction; with it disabled, the user is prompted instead.

[Phase 10 — Credential Manager]

### [Establish the MVC wiring pattern](https://trello.com/c/lBu8pm1q/41-establish-the-mvc-wiring-pattern)

Build the Model/View/Controller pattern once, end-to-end, against the Song Entry model and a minimal results list — this becomes the template every other screen below follows, rather than each screen inventing its own wiring.

Acceptance: a working, minimal search-results list, built the "right" way once, that every later screen can be modeled after rather than redesigned from scratch.

[Phase 11 — Frontend]

### [Login screen](https://trello.com/c/x3rA9YW7/42-login-screen)

Username, password, remember-me, login action — not shown at forced startup, only when an operation actually requires it.

Acceptance: matches the deferred-login behavior already established — the app opens without demanding credentials, and the login screen appears only when triggered by an auth-requiring action.

[Phase 11 — Frontend]

### [Search/Home screen](https://trello.com/c/Ir86AWjy/43-search-home-screen)

Search input, the unified sort control, and the results list, with lazy loading tied to the pagination built earlier. Only entries that already passed the YouTube-link filter ever reach this screen.

Acceptance: scrolling to the end of the currently-loaded results triggers the next page without user action.

[Phase 11 — Frontend]

### [Downloads screen](https://trello.com/c/oky4mgwZ/44-downloads-screen)

Queue, active downloads, progress, status, and errors, reflecting the Download Manager's actual state.

Acceptance: cancelling or retrying from this screen actually reaches the Download Manager — this screen never manages download state itself.

[Phase 11 — Frontend]

### [Settings screen](https://trello.com/c/LKsiLPP6/45-settings-screen)

Sort default, maximum concurrent downloads, storage location, and credential management, all editable in one place.

Acceptance: a change made here takes effect without restarting the app.

[Phase 11 — Frontend]

### [Enforce Controller-only backend access](https://trello.com/c/bCzkxjpQ/46-enforce-controller-only-backend-access)

Confirm no screen imports or calls the USDB Client, Parser, or Download Manager directly — every path goes through a Controller.

Acceptance: a code-level check (even a manual review checklist, if nothing automated exists yet) confirms this boundary holds across every screen built above.

[Phase 11 — Frontend]

### [End-to-end flow verification](https://trello.com/c/PKFm7HIC/47-end-to-end-flow-verification)

Walk the full path — login, search, filter, queue, download — and confirm the resulting local library actually matches what the app believes it downloaded.

Acceptance: a fresh run of the complete flow, against the real site, produces a correct, complete local library with no manual intervention beyond normal use.

[Phase 12 — Integration & Cross-Cutting Concerns]

### [Consistent error handling & logging](https://trello.com/c/YUoaiXsD/48-consistent-error-handling-logging)

Apply the logging/error-handling convention decided in Phase 1 consistently across every component built since — no component inventing its own approach ad hoc.

Acceptance: an error in any layer surfaces to the user in a way consistent with every other layer's errors, not a one-off per component.

[Phase 12 — Integration & Cross-Cutting Concerns]

### [Settings persistence](https://trello.com/c/BU3kkUHT/49-settings-persistence)

Persist Settings-screen values across restarts.

Acceptance: closing and reopening the app retains the user's configured sort default, concurrency limit, storage location, and remember-credentials choice.

[Phase 12 — Integration & Cross-Cutting Concerns]

### [Linux packaging](https://trello.com/c/d82YTw1Q/50-linux-packaging)

Package the app for Linux distribution, tested on more than one distro given the research findings about real, distro-specific breakage in comparable prior art (glibc versioning, missing libraries).

Acceptance: the packaged app runs correctly on at least two meaningfully different Linux distributions, not just the development machine.

[Phase 13 — Packaging & Distribution]

### [Windows packaging](https://trello.com/c/RFZuqNQm/51-windows-packaging)

Package the app for Windows distribution.

Acceptance: the packaged app runs correctly on a clean Windows machine with no development tools installed.

[Phase 13 — Packaging & Distribution]

### [Install / first-run experience](https://trello.com/c/yX5E4vky/52-install-first-run-experience)

A basic install path and a sensible first-run experience — nothing elaborate, just: a new user can get from download to a working app without guesswork.

Acceptance: someone unfamiliar with the project can install and open the app successfully from written instructions alone.

[Phase 13 — Packaging & Distribution]

## WorkingOn

### [Repository structure reflecting SOC boundaries](https://trello.com/c/FnELiaAK/5-repository-structure-reflecting-soc-boundaries)

Set up the project's repository structure so each Separation-of-Concerns component gets its own package/module from day one: USDB Client, Normalization, Parser, Download Manager, Storage Manager, Credential Manager, shared domain models, and the frontend, as distinct top-level packages — not one flat folder.

Acceptance: an empty scaffold exists where every later phase has an obvious, unambiguous home to land in, and importing one concern's code never requires reaching into another's internals.

[Phase 1 — Environment & Project Setup]

## Testing


## Review


## Done

### [Which desktop UI technologies provide good cross-platform support for Linux and Windows?](https://trello.com/c/RFQUgv3W/2-which-desktop-ui-technologies-provide-good-cross-platform-support-for-linux-and-windows)

Answered. Compared three real candidates in depth: Python+PySide6, C#+Avalonia, Rust+Tauri. PySide6 has proven, working prior art for this exact app (USDB Syncer, 2,100+ commits, actively maintained); Avalonia is solid but its own docs list Wayland support as still in private preview; Tauri's Linux story has well-documented, recurring WebKitGTK/GPU-driver issues, including a dedicated official troubleshooting page for them. Decision: Python + PySide6. Full comparison and evidence: technology research doc, Stage 5/6.

### [How good is the language/framework at maintaining complex HTTP sessions and handling web requests?](https://trello.com/c/cXMj4RVI/3-how-good-is-the-language-framework-at-maintaining-complex-http-sessions-and-handling-web-requests)

Answered. Mature and roughly equivalent across all three candidates researched (Python, C#, and Rust all have solid HTTP/session-handling libraries). This did not end up being a real differentiator between the candidates — credential storage and YouTube-download integration did. See the technology research doc, Stage 5/6 comparison matrix.

### [What HTML parsing libraries exist, and how mature are they?](https://trello.com/c/v7J71cLM/4-what-html-parsing-libraries-exist-and-how-mature-are-they)

Answered. Mature options exist for all three candidates researched (Python, C#, and Rust). Not a differentiator in the end. See the technology research doc, Stage 5/6 comparison matrix.

### [Desktop USDB-Scrapper](https://trello.com/c/ZNLhEmCf/1-desktop-usdb-scrapper)

The Framework/Languague we will use throughout the project.

This needs to be able to

- transform and append txt files
- download and store youtube video in MP3/MP4
- Login to the page https://usdb.animux.de with persistent Storage
- read and understand Webpage sources
- only Desktop Application no Webservice

---
Status update: full requirements analysis, USDB technical investigation, architecture, and a three-way technology comparison are done — see the technology research doc. Stack decided: Python + PySide6. A milestone roadmap breaks the build into 14 phases — see the milestone roadmap doc. This card now tracks the project as a whole; phase-level work gets its own cards from here on.
