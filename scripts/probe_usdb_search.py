"""Manual search investigation. Emit metadata only; never save live HTML/cookies."""

import json
import re
import sys
import time
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from usdb_scrapper.credential_manager.terminal import get_credentials
from usdb_scrapper.usdb_client import UsdbError, UsdbSession

ORIGIN = "https://usdb.animux.de/"
SORT_KEY = re.compile(r"sort|order|direction|^ud$", re.I)
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
        self.echoed_filters = {}
        self.direction_controls = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        name = values.get("name") or ""
        if tag in ("input", "select") and SAFE_TOKEN.fullmatch(name):
            # Field names only: never values of hidden/account controls.
            self.fields.add(name)
        if tag == "input" and name in ("interpret", "title"):
            self.echoed_filters[name] = (values.get("value") or "")[:120]
        if tag == "input" and name == "ud":
            value = values.get("value") or ""
            if SAFE_TOKEN.fullmatch(value):
                self.direction_controls.append(
                    {
                        "value": value,
                        "type": values.get("type") or "text",
                        "checked": "checked" in values,
                    }
                )
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
            "echoed_search_filters": self.echoed_filters,
            "direction_controls": self.direction_controls,
            "sort_link_parameters": self.sort_links,
            "sort_option_values": self.sort_options,
        }


def search_fields(fields):
    # Omitted fields may inherit the previous search from the server session.
    return {"details": "1", "interpret": "", "title": "", "start": "0", **fields}


def compact(summary):
    return {
        key: summary[key]
        for key in (
            "candidate_song_ids_in_page_order",
            "candidate_song_count_on_page",
            "echoed_search_filters",
        )
    }


def main():
    if not sys.stdin.isatty():
        print("Run in your own terminal; do not pipe credentials.")
        return 2
    try:
        username, password = get_credentials()
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
            controls = SearchSummary(session.get_html()).summary()
            report["listing_controls"] = controls
            directions = list(
                dict.fromkeys(
                    controls["sort_option_values"].get("ud", [])
                    + [item["value"] for item in controls["direction_controls"]]
                )
            )
            cases += [
                ("id_sort_" + str(index), {"title": "Dancing Queen", "order": "id", "ud": value})
                for index, value in enumerate(directions[:2])
            ]
            cases.append(("title_control_after_negative", {"title": "Dancing Queen"}))
            for label, fields in cases:
                time.sleep(1)
                submitted = search_fields(fields)
                html = session.post_html("/?link=list", submitted)
                summary = SearchSummary(html).summary()
                report["queries"][label] = {"submitted": submitted, **compact(summary)}
                if label.startswith("id_sort_"):
                    ids = summary["candidate_song_ids_in_page_order"]
                    report["queries"][label].update(
                        ids_ascending=bool(ids) and ids == sorted(ids),
                        ids_descending=bool(ids) and ids == sorted(ids, reverse=True),
                    )
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
