import pytest

from usdb_scrapper.parser import LocalMedia, TxtExportError, parse_txt, serialize_v1_txt

MEDIA = LocalMedia(audio="song.mp3", video="song.mp4", cover="song.jpg")
TEXT = "#TITLE:Café\n#ARTIST:A\n#MP3:old.mp3\n#BPM:120,5\n#VIDEO:v=abcdefghijk\n"
TIMING = (
    "#GAP:1250\n#START:2.5\n#END:4000\n#VIDEOGAP:-0.25\n#PREVIEWSTART:3.25\n#MEDLEYSTARTBEAT:8\n"
)
BODY = ": 0 4 2 héllo  \r\n- 4\r\nE\r\n"


def test_player_export_preserves_timing_notes_and_is_idempotent():
    source = parse_txt(TEXT + TIMING + BODY)
    data = serialize_v1_txt(source, MEDIA)
    text = data.decode("utf-8")
    assert text.startswith("#VERSION:1.0.0\n")
    assert "#AUDIO:song.mp3\n" in text and "#MP3:" not in text
    assert "#BPM:120,5\n" in text and TIMING in text
    assert text.endswith(BODY)
    assert serialize_v1_txt(parse_txt(text), MEDIA) == data
    assert source.song.version is None


@pytest.mark.parametrize(
    "header", ["#VERSION:2.0.0", "#VERSION:3.0.0", "#RELATIVE:YES", "#NOTESGAP:2", "#RESOLUTION:4"]
)
def test_incompatible_timing_is_not_silently_relabelled(header):
    with pytest.raises(TxtExportError):
        serialize_v1_txt(parse_txt(header + "\n" + TEXT + BODY), MEDIA)


def test_encoding_and_legacy_duet_labels():
    result = serialize_v1_txt(
        parse_txt(TEXT + "#ENCODING:CP1252\n#DUETSINGERP1:Lead\n" + BODY), MEDIA
    )
    assert b"ENCODING" not in result
    assert b"#P1:Lead\n" in result
    assert b"DUETSINGERP1" not in result
