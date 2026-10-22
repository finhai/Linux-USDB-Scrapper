# Library transactions and recovery

Each download acquires an OS-backed per-song lock and records a journal before
creating staged files. Publication requires four complete, nonempty files.
Existing directories containing unexpected files are preserved and rejected.

Identical bundles are discarded after chunked (1 MiB) comparison, preserving
existing mtimes. Changed bundles back up the original files, then atomically
replace each final file, with TXT last. Final paths remain present throughout.
Each file is wholly old or new; readers can temporarily observe a mixture of
bundle generations. This is per-file atomic replacement, not an atomic four-file
transaction. A committed journal marks successful publication before cleanup.

Startup recovery skips active locks. Interrupted replacement restores all original
files through atomic replacements; committed transactions retain the new bundle.
Backup files remain available until rollback finishes, so recovery can be retried.
Invalid journals and symlinks are preserved for inspection. Arbitrary directories
are never deleted merely because their names resemble staging directories.

Tests kill a separate process during staging, after the first file replacement,
and after publication. Restart restores a complete old or new four-file bundle.
This covers process crashes; power-loss durability is not claimed. Lock files
remain as harmless bookkeeping beside song folders.
