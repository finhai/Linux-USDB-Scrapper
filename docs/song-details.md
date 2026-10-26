# Song-detail YouTube extraction — card 20

DetailClient(session).fetch(song_id) reads /?link=detail&id=<id> through the
session's public get_html method. It returns SongDetails(song_id, youtube_urls).
An empty tuple explicitly means no supported video reference was found in the
verified comments section. A missing/wrong page or unrecognized comments structure
raises DetailParseError; HTTP/authentication failures propagate from the session.

The observed page has a matching detail/comment form and a table headed
“Comments by users (two cents)”. Extraction stops at “Write Comment” or the end
of that table. Scripts, styles, forms, editor text and links outside the section
are excluded. Positive integer IDs are validated before sending a request.

Supported references include links, bare URLs, BBCode-wrapped URLs, and embedded
players. Known YouTube hosts and video paths are checked, 11-character video IDs
are validated, and results become canonical HTTPS watch URLs. Tracking/time query
parameters are discarded. Equivalent references are deduplicated; multiple videos
remain available in encounter order. No relevance ranking or video availability
check is claimed. Malformed/unsupported references are ignored, so an empty tuple
means no supported reference, not proof that no video exists anywhere.

Cover retrieval is independent and is not part of this change. GUI, download and
pipeline integration remain later work. Returned page contents are never logged.

## Validation (2026-10-20)

Public unauthenticated reads showed the actual rendered comment structure; no
credentials were needed or retained. DetailClient using a public read adapter
successfully extracted URLs for IDs 3289, 9, 37 and 4439. The 3289 embed normalized
to https://www.youtube.com/watch?v=xFrGuyw1V8s. Further parser checks on IDs 50, 88,
148, 157, 174 and 204 each found one reference. These public reads validate the
parser/protocol; they do not independently test authenticated session integration.

No-video behavior is covered by a synthetic verified comment section without a
video. All ten inspected real examples had a video; live absence is not claimed.
Offline cases also cover BBCode, embeds, links, duplicate/multiple videos, deceptive
hosts, nonvideo URLs, wrong pages and exclusion of editor/script references.

This feature depends on PR #12. Reconcile and retarget to dev after prerequisite
integration so CI can run before merging.
