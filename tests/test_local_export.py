from dataclasses import replace

import pytest

from usdb_scrapper.parser import LocalMedia, TxtExportError, parse_txt, serialize_local_txt

TEXT = (
    "#TITLE:Example\n#ARTIST:Example\n#MP3:old.mp3\n#BPM:120\n"
    "#VIDEO:v=abcdefghijk,co=remote.jpg,bg=background.jpg\n#GAP:1200\n"
    ": 0 4 2  exact  \r\n- 4\r\nE\r\n"
)
MEDIA = LocalMedia(audio="song.flac", video="song.mp4", cover="cover.jpg")


def test_rewrite_and_reparse_preserves_notes_and_timing():
    original = parse_txt(TEXT)
    output = serialize_local_txt(original, MEDIA)
    updated = parse_txt(output)
    assert updated.song.note_block.encode() == original.song.note_block.encode()
    assert updated.song.bpm == original.song.bpm
    assert updated.extra_headers == original.extra_headers
    assert (updated.song.audio, updated.song.video, updated.song.cover) == (
        "song.flac",
        "song.mp4",
        "cover.jpg",
    )
    assert updated.video_metadata == ()
    assert original.video_metadata != ()
    assert "#MP3:" not in output
    assert "abcdefghijk" not in output
    assert "remote.jpg" not in output


@pytest.mark.parametrize(
    "filename",
    ["../x", "/tmp/x", "C:\\x", "https://youtu.be/x", "x\n#VIDEO:y", "", "v=abcdefghijk"],
)
def test_reject_nonlocal_media(filename):
    with pytest.raises(TxtExportError):
        LocalMedia(audio=filename, video="video.mp4", cover="cover.jpg")


@pytest.mark.parametrize("value", ["https://youtu.be/abcdefghijk", "abcdefghijk", "v=abcdefghijk"])
def test_preserved_text_with_remote_reference_rejects_export(value):
    original = parse_txt(TEXT)
    for modified in (
        replace(original, song=replace(original.song, title=value)),
        replace(original, song=replace(original.song, note_block=original.song.note_block + value)),
        replace(original, extra_headers=(("COMMENT", value),)),
    ):
        with pytest.raises(TxtExportError):
            serialize_local_txt(modified, MEDIA)


def test_extra_header_cannot_override_local_media():
    with pytest.raises(TxtExportError):
        serialize_local_txt(replace(parse_txt(TEXT), extra_headers=(("VIDEO", "bad"),)), MEDIA)
