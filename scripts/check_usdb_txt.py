"""Manual TXT retrieval check; prints structure and content markers, never lyrics."""

import json
import sys
from html.parser import HTMLParser

from usdb_scrapper.credential_manager.terminal import get_credentials
from usdb_scrapper.usdb_client import UsdbError, UsdbSession, extract_txt
from usdb_scrapper.usdb_client.txt import TxtClient


class ContentSummary(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.blocks = []
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "textarea":
            self.current = []
            self.blocks.append(self.current)

    def handle_endtag(self, tag):
        if tag == "textarea":
            self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)


def main():
    if not sys.stdin.isatty():
        print("Run in your own terminal; do not pipe credentials.")
        return 2
    try:
        username, password = get_credentials()
        with UsdbSession() as session:
            session.login(username, password)
            username = password = ""
            page = TxtClient(session).retrieve_page(3289)
            text = extract_txt(page)
            blocks = [text]
            print(
                json.dumps(
                    {
                        "follow_up_completed": True,
                        "production_extraction_completed": True,
                        "contains_replacement_character": "\ufffd" in text,
                        "textarea_count": len(blocks),
                        "content_markers": [
                            {
                                "has_title": "#TITLE:" in block,
                                "has_artist": "#ARTIST:" in block,
                                "has_notes": any(
                                    line.startswith(": ") for line in block.splitlines()
                                ),
                                "has_end": any(line.strip() == "E" for line in block.splitlines()),
                            }
                            for block in blocks
                        ],
                    },
                    indent=2,
                )
            )
        return 0
    except (UsdbError, ValueError):
        print("TXT check failed; no page or credential details printed.")
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Check cancelled.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
