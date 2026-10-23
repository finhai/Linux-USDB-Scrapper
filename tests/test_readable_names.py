from pathlib import PureWindowsPath

import pytest

from usdb_scrapper.normalization.filesystem import readable_filesystem_name


@pytest.mark.parametrize(
    "name", ["Björk", "Sexyy Red & Bruno Mars", "Fat Juicy & Wet [EXPLICIT]", "東京"]
)
def test_normal_names_stay_readable(name):
    assert readable_filesystem_name(name) == name


@pytest.mark.parametrize("name", ["CON", "A/B", "../", "a" * 300, "\x00", "COM¹"])
def test_invalid_names_are_portable(name):
    result = readable_filesystem_name(name)
    assert not PureWindowsPath(result).is_reserved()
    assert PureWindowsPath(result).name == result
    assert len(result.encode()) <= 101
    assert not result.endswith((" ", "."))


def test_lossy_names_do_not_collide():
    assert readable_filesystem_name("A/B") != readable_filesystem_name("A-B")
