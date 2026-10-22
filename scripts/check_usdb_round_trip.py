"""Live fidelity acceptance; reports booleans, never raw song data."""

import json
import sys

from usdb_scrapper.credential_manager.terminal import get_credentials
from usdb_scrapper.parser import (
    LocalMedia,
    TxtExportError,
    TxtParseError,
    parse_txt,
    serialize_local_txt,
    serialize_v2_txt,
)
from usdb_scrapper.usdb_client import TxtClient, UsdbError, UsdbSession


def report_round_trip(text):
    media = LocalMedia(audio="song.flac", video="video.mp4", cover="cover.jpg")
    original = parse_txt(text)
    local = serialize_local_txt(original, media)
    reparsed = parse_txt(local)
    media_keys = {"MP3", "AUDIO", "VIDEO", "COVER"}

    def unaffected(parsed, excluded=media_keys):
        return "".join(
            line
            for line in parsed.source_headers
            if line[1:].partition(":")[0].upper() not in excluded
        )

    report = {
        "media_only_notes_identical": reparsed.song.note_block.encode()
        == original.song.note_block.encode(),
        "media_only_other_headers_identical": unaffected(original).encode()
        == unaffected(reparsed).encode(),
        "local_media_correct": (reparsed.song.audio, reparsed.song.video, reparsed.song.cover)
        == (media.audio, media.video, media.cover),
    }
    try:
        data = serialize_v2_txt(original, media)
        v2 = parse_txt(data.decode("utf-8"))
        report.update(
            v2_exported=True,
            v2_other_headers_identical=unaffected(
                original,
                media_keys
                | {
                    "VERSION",
                    "BPM",
                    "ENCODING",
                    "GAP",
                    "START",
                    "END",
                    "VIDEOGAP",
                    "PREVIEWSTART",
                    "MEDLEYSTARTBEAT",
                    "MEDLEYENDBEAT",
                    "MEDLEYSTART",
                    "MEDLEYEND",
                },
            ).encode()
            == unaffected(
                v2,
                media_keys
                | {
                    "VERSION",
                    "BPM",
                    "ENCODING",
                    "GAP",
                    "START",
                    "END",
                    "VIDEOGAP",
                    "PREVIEWSTART",
                    "MEDLEYSTARTBEAT",
                    "MEDLEYENDBEAT",
                    "MEDLEYSTART",
                    "MEDLEYEND",
                },
            ).encode(),
            v2_notes_identical=v2.song.note_block == original.song.note_block,
            v2_second_export_identical=serialize_v2_txt(v2, media) == data,
            v2_version_correct=v2.song.version == "2.0.0",
        )
    except TxtExportError as exc:
        report.update(v2_exported=False, v2_error=str(exc))
    return report


def main():
    if not sys.stdin.isatty():
        print("Run in your own terminal; do not pipe credentials.")
        return 2
    try:
        username, password = get_credentials()
        with UsdbSession() as session:
            session.login(username, password)
            username = password = ""
            text = TxtClient(session).retrieve_text(3289)
        report = report_round_trip(text)
        print(json.dumps(report, indent=2))
        return 0 if all(value is True for value in report.values()) else 1
    except (UsdbError, TxtParseError, TxtExportError) as exc:
        print(json.dumps({"completed": False, "error": str(exc)}))
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Check cancelled.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
