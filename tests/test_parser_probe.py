import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "parser_probe", Path(__file__).parents[1] / "scripts/check_usdb_parser.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_diagnostic_identifies_compound_video_without_exposing_values():
    text = (
        "#TITLE:private-title\n#ARTIST:private-artist\n#MP3:private-file.mp3\n"
        "#BPM:120\n#VIDEO:v=abcdefghijk,co=private-cover\n: 0 1 2 private-lyrics\nE\n"
    )
    result = probe.summarize_parser(text)
    assert result["parsed"]
    assert result["video_structure"]["known_meta_keys"] == ["v", "co"]
    assert result["video_structure"]["contains_comma"]
    assert "private" not in json.dumps(result)
    assert "abcdefghijk" not in json.dumps(result)


def test_diagnostic_accepts_legacy_without_version_or_cover():
    result = probe.summarize_parser(
        "#TITLE:Example\n#ARTIST:Example\n#MP3:song.mp3\n#BPM:120\n"
        "#VIDEO:v=abcdefghijk\n: 0 1 2 sample\nE\n"
    )
    assert result["parsed"]
    assert result["version_absent"] and result["cover_absent"]
