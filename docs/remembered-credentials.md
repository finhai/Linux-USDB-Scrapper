# Remember USDB credentials for checks

Run `.venv/bin/python scripts/remember_usdb.py save` once from the project folder.
Enter credentials at hidden prompts and unlock the desktop keyring if requested.
The command verifies USDB login before saving, then verifies reading it back.
Both username and password are stored together in a native-keyring secret.

Later check/probe scripts use it automatically. Run
`.venv/bin/python scripts/remember_usdb.py check` in a new process to verify reuse
without typing USDB credentials. `forget` removes this application's entry.
To change credentials, run `save` again. Failed logins do not overwrite the entry.

Linux uses Secret Service explicitly (a running, unlocked desktop keyring is
needed); Windows uses Credential Locker. No automatically selected third-party
or plaintext fallback is allowed. If unavailable, manual checks fall back to
hidden prompts. Locked stores may show an OS unlock prompt. There is no GUI
settings integration yet, and Windows/native restart acceptance is pending.

Backend failures are sanitized, and credential object representations omit both
values. The secret is not saved in project files, environment variables or
shell command arguments. Credentials exist in process memory while used.
The sandbox may not access the desktop bus; run setup/checks in your own terminal.

Reference: https://keyring.readthedocs.io/en/latest/

Live Linux verification on 2026-10-21: save returned remembered=true and
login_verified=true. A subsequent separate check process returned the same
result without USDB credential prompts. This verifies native storage and
cross-process reuse; Windows and full desktop-reboot checks remain pending.
