"""Manual search investigation. Emit metadata only; never save live HTML/cookies."""

import getpass
import json
import re
import sys
import time
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from usdb_scrapper.usdb_client import UsdbError, UsdbSession

ORIGIN = "https://usdb.animux.de/"
SORT_KEY = re.compile(r"sort|order|direction", re.I)
SAFE_TOKEN = re.compile(r"[A-Za-z0-9_. -]{0,60}\Z")


class SearchSummary(HTMLParser):
    """Best-effort protocol discovery, not a production result parser."""

    def __init__(self, html):
        super().__init__()
        self.ids = []
        self.id_links = set()
        self.sort_links = []
        self.fields = set()
        self.sort_options = {}
        self.select = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        name = values.get("name") or ""
        if tag in ("input", "select") and SAFE_TOKEN.fullmatch(name):
            # Field names only: never values of hidden/account controls.
            self.fields.add(name)
        if tag == "select":
            self.select = name if SORT_KEY.search(name) else None
        if tag == "option" and self.select:
            value = values.get("value") or ""
            if SAFE_TOKEN.fullmatch(value):
                self.sort_options.setdefault(self.select, []).append(value)
        if tag != "a":
            return
        try:
            url = urlsplit(urljoin(ORIGIN, values.get("href") or ""))
        except ValueError:
            return
        if url.scheme != "https" or url.netloc != "usdb.animux.de":
            return
        query = parse_qs(url.query)
        link = query.get("link", [""])[0]
        # Candidate entry links only; exclude profiles, downloads and navigation.
        if link == "detail":
            song_id = query.get("id", [""])[0]
            if song_id.isascii() and song_id.isdigit() and int(song_id) > 0:
                self.id_links.add(link)
                if int(song_id) not in self.ids:
                    self.ids.append(int(song_id))
        sort = {
            key: val
            for key, val in query.items()
            if SORT_KEY.search(key)
            and SAFE_TOKEN.fullmatch(key)
            and all(SAFE_TOKEN.fullmatch(item) for item in val)
        }
        if link == "list" and sort and sort not in self.sort_links:
            self.sort_links.append(sort)

    def handle_endtag(self, tag):
        if tag == "select":
            self.select = None

    def summary(self):
        return {
            "candidate_song_ids_in_page_order": self.ids,
            "candidate_song_count_on_page": len(self.ids),
            "candidate_link_types": sorted(self.id_links),
            "field_names": sorted(self.fields),
            "sort_link_parameters": self.sort_links,
            "sort_option_values": self.sort_options,
        }


def main():
    if not sys.stdin.isatty():
        print("Run in your own terminal; do not pipe credentials.")
        return 2
    try:
        username = getpass.getpass("USDB username (hidden): ")
        password = getpass.getpass("USDB password (hidden): ")
        cases = [
            ("artist_only", {"interpret": "ABBA"}),
            ("title_only", {"title": "Dancing Queen"}),
            ("combined", {"interpret": "ABBA", "title": "Dancing Queen"}),
            (
                "combined_unmatched_artist",
                {"interpret": "USDBProbeNoSuchArtist7e8a491c", "title": "Dancing Queen"},
            ),
            *[
                ("normalization_" + str(i), {"title": title})
                for i, title in enumerate(
                    ["Don't Stop", "Dont Stop", "dont stop", "Dónt Stóp"], start=1
                )
            ],
        ]
        report = {
            "scope": "first response pages only; candidates are not verified result rows",
            "queries": {},
        }
        with UsdbSession() as session:
            session.login(username, password)
            username = password = ""
            report["listing_controls"] = SearchSummary(session.get_html()).summary()
            for label, fields in cases:
                time.sleep(1)
                html = session.post_html("/?link=list", {"details": "1", **fields})
                report["queries"][label] = {"submitted": fields, **SearchSummary(html).summary()}
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (UsdbError, ValueError):
        print("Search probe failed; no page or credential details were printed.")
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Probe cancelled.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
