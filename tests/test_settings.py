from dataclasses import replace

import pytest

from usdb_scrapper.storage_manager.settings import Settings, SettingsError, SettingsStore


def test_round_trip_and_default(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    assert store.load() == Settings()
    expected = replace(
        Settings(),
        storage_root=str(tmp_path),
        concurrency=4,
        sort_field="title",
        sort_direction="desc",
        remember=False,
    )
    store.save(expected)
    assert SettingsStore(store.path).load() == expected
    assert "password" not in store.path.read_text()


def test_invalid_file_kept_for_recovery(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    store.path.write_text("{broken")
    with pytest.raises(SettingsError):
        store.load()
    assert store.path.read_text() == "{broken"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"concurrency": True},
        {"concurrency": 0},
        {"storage_root": "../songs"},
        {"sort_field": "unknown"},
        {"remember": "false"},
    ],
)
def test_validation(kwargs):
    with pytest.raises(SettingsError):
        Settings(**kwargs)
