# Replaceable media downloads (card 34)

`MediaDownloader` defines async `audio(url, target)` and `video(url, target)`.
`DownloadSources` combines an implementation with independent async TXT and cover
providers and satisfies `BundleSource`. Replacing the media object requires no
queue, bundle or storage changes. An offline bundle test exercises two implementations.

`YtDlpDownloader` invokes an external yt-dlp executable without a shell or user
configuration. It canonicalizes YouTube URLs, requests MP3 extraction or MP4
streams, uses an isolated temporary directory, and publishes a nonempty result
without overwriting an existing target. Timeout and cancellation stop the POSIX
process group, including conversion children, before cleaning temporary files.
No USDB credentials or browser cookies are sent to the downloader.

Install and maintain yt-dlp, FFmpeg and ffprobe separately on PATH. A custom
executable path may be passed to the adapter. These external binaries are not
pinned by uv.lock; packaging/version selection is still pending. CLI options follow
[yt-dlp's documentation](https://github.com/yt-dlp/yt-dlp#usage-and-options).

Current implementation is Linux/POSIX only; Windows fails explicitly until a
process-tree implementation is available. Live YouTube download/conversion has
not been verified: FFmpeg/ffprobe were unavailable on the development PATH.
Offline tests use synthetic bytes and do not establish playback compatibility.
MP4 selection does not guarantee a particular player-supported codec.

The app still needs a real cover provider, application wiring, and download UI.
No assumption is made that a YouTube thumbnail equals the requested USDB cover.
Progress reporting, retries and GUI cancellation controls remain card 31 work.
Targets must be inside a caller-owned staging directory on the same filesystem;
concurrent writes to the same target are unsupported. Native hard-link support
is required for publication.


2026-10-21 integration update: the default adapter now invokes the project's locked
yt-dlp module (or a packaged media-worker entry point). FFmpeg lookup supports
PATH, USDB_FFMPEG_DIR, packaged tools and this checkout's local tools. Linux live
audio/video retrieval succeeded for Song 3289. Windows uses psutil process-tree
termination, but clean-Windows validation is pending. Preferred video selection
is now H.264 MP4 up to 1080p with AAC. The original AV1 live sample was valid media
but did not establish UltraStar playback compatibility.
