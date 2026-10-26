"""Live parser check; no song text or credential values are printed."""

import json
import re
import sys
from decimal import Decimal, InvalidOperation

from usdb_scrapper.credential_manager.terminal import get_credentials
from usdb_scrapper.parser import TxtParseError, parse_txt
from usdb_scrapper.usdb_client import TxtClient, UsdbError, UsdbSession


def summarize_parser(text):
    """Return structural diagnostics only; never header values or note contents."""
    names = []
    values = {}
    for line in text.removeprefix("\ufeff").splitlines():
        if not line.startswith("#"):
            break
        name, separator, value = line[1:].partition(":")
        if separator:
            names.append(name.upper())
            values[name.upper()] = value.strip()
    video = values.get("VIDEO", "")
    prefix = re.match(r"v=([A-Za-z0-9_-]{11})(.*)", video)
    try:
        bpm = Decimal(values.get("BPM", "").replace(",", "."))
        bpm_valid = bpm.is_finite() and bpm > 0
    except InvalidOperation:
        bpm_valid = False
    report = {
        "legacy_mp3_present": "MP3" in names,
        "video_meta_present": video.startswith("v="),
        "missing_optional_fields": [name for name in ("VERSION", "COVER") if name not in names],
        "missing_required_fields": [
            name for name in ("TITLE", "ARTIST", "BPM", "VIDEO") if name not in names
        ]
        + ([] if "AUDIO" in names or "MP3" in names else ["AUDIO/MP3"]),
        "duplicate_headers": len(names) != len(set(names)),
        "blank_known_fields": [
            name
            for name in ("TITLE", "ARTIST", "BPM", "AUDIO", "MP3", "VIDEO")
            if name in values and not values[name]
        ],
        "bpm_valid": bpm_valid,
        "video_structure": {
            "standalone_id": bool(re.fullmatch(r"v=[A-Za-z0-9_-]{11}", video)),
            "starts_with_id": prefix is not None,
            "suffix_length": len(prefix[2]) if prefix else None,
            "contains_comma": "," in video,
            "contains_semicolon": ";" in video,
            "contains_ampersand": "&" in video,
            "contains_whitespace": any(c.isspace() for c in video),
            "known_meta_keys": [
                key
                for key in ("v", "a", "co", "bg", "start", "end", "gap")
                if re.search(r"(?:^|[ ,;&])" + key + "=", video)
            ],
        },
    }
    try:
        parsed = parse_txt(text)
        report.update(
            parsed=True,
            positive_bpm=parsed.song.bpm > 0,
            has_note_block=bool(parsed.song.note_block),
            version_absent=parsed.song.version is None,
            cover_absent=parsed.song.cover is None,
            additional_video_metadata_count=len(parsed.video_metadata),
        )
    except TxtParseError as exc:
        report.update(parsed=False, error=str(exc))
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
        report = summarize_parser(text)
        print(json.dumps(report, indent=2))
        return 0
    except (UsdbError, ValueError):
        print("Parser check failed; no page or credential details printed.")
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Check cancelled.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
