# Library transactions and recovery

Each song download acquires an OS-backed per-song lock. A journal records its
staging/backup names before staged files are created. A complete staging directory
is verified before publication. Existing directories with unexpected files are
preserved and rejected, rather than deleting user additions.

Identical bundles are discarded after chunked (1 MiB) comparison; existing mtimes
remain unchanged. Different complete bundles replace the song directory using
old-to-backup and staging-to-final renames. There is a brief absent-path interval
between renames. This is recoverable complete-directory replacement, not a single
atomic exchange on every platform. Card 33's strict uninterrupted atomic-path
acceptance therefore remains open.

On startup, the selected library's artist directories are scanned for app journals.
Active locks are skipped. If publication stopped after moving the old directory,
recovery restores it. If the new directory was published, recovery removes the
backup and staging debris. Invalid journals/symlinks are preserved for inspection.
There is no automatic deletion of arbitrary directories based only on a prefix.

Tests kill a separate process during staging, after moving the original, and after
publishing the replacement. Restart recovers a complete old or new four-file
bundle. This covers process crashes; power-loss/filesystem durability is not
claimed. OS lock files remain as harmless bookkeeping files beside song folders.
