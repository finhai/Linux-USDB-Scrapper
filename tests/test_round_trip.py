from dataclasses import replace

import pytest

from usdb_scrapper.parser import LocalMedia, parse_txt, serialize_local_txt, serialize_v2_txt

MEDIA = LocalMedia(audio="song.flac", video="video.mp4", cover="cover.jpg")


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_unchanged_header_bytes_and_notes_survive_media_changes(ending):
    untouched = ["#artist:  Björk  ", "#TITLE:Café ", "#COMMENT: a:b  ", "#GAP:00120"]
    source = ending.join(
        [
            untouched[0],
            "#MP3:old.mp3",
            untouched[1],
            "#BPM:120",
            untouched[2],
            "#VIDEO:v=abcdefghijk",
            untouched[3],
        ]
    )
    body = ": 0 4 2  word  " + ending + "- 4" + ending + "E"
    source += ending + body
    before = parse_txt(source)
    output = serialize_local_txt(before, MEDIA)
    after = parse_txt(output)
    for line in untouched:
        assert (line + ending).encode() in output.encode()
    assert after.song.note_block.encode() == body.encode()
    assert after.song.title == before.song.title
    assert after.extra_headers == before.extra_headers
    assert before.song.audio == "old.mp3"


def test_v2_migration_changes_only_authorized_fields():
    source = (
        "#TITLE:  Café  \r\n#ARTIST:Example\r\n#BPM:120\r\n#MP3:old.mp3\r\n"
        "#VIDEO:v=abcdefghijk\r\n#COMMENT: keep  \r\n#START:1.25\r\n"
        ": 0 4 2 test  \r\nE\r\n"
    )
    parsed = parse_txt(source)
    data = serialize_v2_txt(parsed, MEDIA)
    assert b"#COMMENT: keep  \r\n" in data
    assert "#TITLE:  Café  \r\n".encode() in data
    assert b"#START:1250\r\n" in data
    reparsed = parse_txt(data.decode())
    assert reparsed.song.note_block == parsed.song.note_block
    assert serialize_v2_txt(reparsed, MEDIA) == data


def test_modified_metadata_does_not_reuse_stale_source_line():
    parsed = parse_txt("#TITLE:Old\n#ARTIST:A\n#MP3:a.mp3\n#BPM:120\n#VIDEO:v=abcdefghijk\nE\n")
    changed = replace(parsed, song=replace(parsed.song, title="New"))
    assert "#TITLE:New\n" in serialize_local_txt(changed, MEDIA)
    assert "#TITLE:Old" not in serialize_local_txt(changed, MEDIA)


def test_media_only_export_preserves_decimal_comma_bpm():
    parsed = parse_txt("#TITLE:T\n#ARTIST:A\n#MP3:a.mp3\n#BPM:120,50\n#VIDEO:v=abcdefghijk\nE\n")
    assert "#BPM:120,50\n" in serialize_local_txt(parsed, MEDIA)
    assert b"#BPM:482.00\n" in serialize_v2_txt(parsed, MEDIA)


def test_live_report_uses_real_pipeline_and_detects_changed_header(monkeypatch):
    import runpy
    from pathlib import Path

    probe = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check_usdb_round_trip.py"))
    report = probe["report_round_trip"]
    source = "#TITLE:T\n#ARTIST:A\n#MP3:a.mp3\n#BPM:120\n#VIDEO:v=abcdefghijk\nE\n"
    assert all(value is True for value in report(source).values())
    original_export = report.__globals__["serialize_local_txt"]
    monkeypatch.setitem(
        report.__globals__,
        "serialize_local_txt",
        lambda *args: original_export(*args).replace("#TITLE:T", "#TITLE:Changed"),
    )
    assert report(source)["media_only_other_headers_identical"] is False
