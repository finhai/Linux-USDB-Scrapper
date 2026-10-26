# Four-file bundle worker (card 30)

BundleWorker is an injectable DownloadQueue worker. BundleSource supplies async
TXT parsing and audio/video/cover transfers. The worker validates v2 export,
stages transfers, writes TXT using final local filenames, then verifies all four
nonempty regular files before publishing the new directory. A failure propagates
to the queue's FAILED state; successful publication permits COMPLETED.

Staging sits beside the final directory. Failed or cancelled work removes its
staging directory. Existing destinations fail without replacing their contents.
This first storage path assumes exclusive ownership of the destination namespace
and only supports new song directories. Cross-process arbitration, updates,
crash durability/recovery and resumable downloads belong to later storage cards.
Do not share an authenticated synchronous HTTP session across concurrent workers;
adapters must own sessions and avoid blocking the event loop.

The worker checks presence and size, not media decodability. Adapters must verify
formats and write exactly the requested paths. Tests use explicitly synthetic
media bytes and real temporary filesystem directories; they are not evidence of
successful live media downloading.

Offline tests cover completed bundles, each transfer failure, adapters that
return without a file, empty output, cancellation cleanup and existing-library
preservation. Live BundleSource media adapters are not yet implemented; card 30
remains Testing until a real TXT/audio/video/cover bundle is retrieved and checked.
No GUI download command is available yet.
