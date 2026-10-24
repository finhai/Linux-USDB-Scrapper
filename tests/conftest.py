"""Keep test coordination state out of the real user's application directories."""

import pytest


@pytest.fixture(autouse=True)
def isolated_lock_state(tmp_path, monkeypatch):
    # Child processes inherit these values for crash/recovery and desktop tests.
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "app-state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "app-state"))
