"""Bounded live pagination discovery; no raw pages or account controls emitted."""

import json
import sys
import time
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from usdb_scrapper.credential_manager.terminal import get_credentials
from usdb_scrapper.usdb_client import UsdbError, UsdbSession


class ListingStructure(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.stack = []
        self.rows = []
        self.headers = []
        self.page_controls = []
        self.ignored = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.ignored += 1
        if tag == "tr":
            if self.stack:
                self.stack[-1]["nested"] = True
            self.stack.append(
                {"cells": [], "ids": [], "sort_fields": [], "nested": False, "cell": None}
            )
        if tag in ("td", "th") and self.stack:
            row = self.stack[-1]
            row["cell"] = {"text": [], "images": [], "song_ids": []}
            row["cells"].append(row["cell"])
        if tag == "img" and self.stack and self.stack[-1]["cell"] is not None:
            # Only visible image labels, never URLs or arbitrary attributes.
            self.stack[-1]["cell"]["images"].append(
                {key: attrs[key][:80] for key in ("alt", "title") if attrs.get(key)}
            )
        if tag != "a":
            return
        try:
            url = urlsplit(urljoin("https://usdb.animux.de/", attrs.get("href") or ""))
        except ValueError:
            return
        if url.scheme != "https" or url.netloc != "usdb.animux.de":
            return
        query = parse_qs(url.query)
        link = query.get("link", [""])[0]
        if link == "detail" and self.stack:
            value = query.get("id", [""])[0]
            if value.isascii() and value.isdigit() and int(value) > 0:
                row = self.stack[-1]
                row["ids"].append(int(value))
                if row["cell"] is not None:
                    row["cell"]["song_ids"].append(int(value))
        if link == "list":
            if self.stack and query.get("order"):
                self.stack[-1]["sort_fields"].append(
                    {
                        "cell": len(self.stack[-1]["cells"]) - 1,
                        "order": query["order"][0][:30],
                    }
                )
            controls = {
                key: val
                for key, val in query.items()
                if key in ("start", "limit") and all(x.isascii() and x.isdigit() for x in val)
            }
            if controls and controls not in self.page_controls:
                self.page_controls.append(controls)

    def handle_data(self, data):
        if self.stack and not self.ignored and self.stack[-1]["cell"] is not None:
            self.stack[-1]["cell"]["text"].append(data)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignored = max(0, self.ignored - 1)
        if tag in ("td", "th") and self.stack:
            self.stack[-1]["cell"] = None
        if tag != "tr" or not self.stack:
            return
        row = self.stack.pop()
        if row["nested"]:
            return  # Exclude layout rows containing account/navigation widgets.
        if row["ids"]:
            self.rows.append(
                {
                    "song_ids": list(dict.fromkeys(row["ids"])),
                    "cells": [
                        {**cell, "text": " ".join(" ".join(cell["text"]).split())[:160]}
                        for cell in row["cells"]
                    ],
                }
            )
        elif row["sort_fields"]:
            self.headers.append(row["sort_fields"])

    def summary(self):
        ids = [song_id for row in self.rows for song_id in row["song_ids"]]
        return {
            "candidate_row_count": len(self.rows),
            "candidate_ids": ids,
            "duplicate_ids": len(ids) != len(set(ids)),
            "sample_rows": self.rows[:2],
            "sort_header_cells": self.headers,
            "page_controls": self.page_controls[:8],
        }


def main():
    if not sys.stdin.isatty():
        print("Run in your own terminal; do not pipe credentials.")
        return 2
    try:
        username, password = get_credentials()
        report = {
            "scope": "candidate leaf table rows; not yet a validated result parser",
            "pages": {},
        }
        with UsdbSession() as session:
            session.login(username, password)
            username = password = ""
            for name, start, limit in (
                ("first", 0, 100),
                ("second", 100, 100),
                ("boundary", 90, 30),
            ):
                time.sleep(1)
                fields = {
                    "details": "1",
                    "interpret": "",
                    "title": "Love",
                    "order": "id",
                    "ud": "asc",
                    "start": str(start),
                    "limit": str(limit),
                }
                page = ListingStructure(session.post_html("/?link=list", fields)).summary()
                report["pages"][name] = {"submitted": fields, **page}
        first = report["pages"]["first"]["candidate_ids"]
        second = report["pages"]["second"]["candidate_ids"]
        boundary = report["pages"]["boundary"]["candidate_ids"]
        report["checks"] = {
            "first_page_has_100_candidates": len(first) == 100,
            "second_page_nonempty": bool(second),
            "pages_disjoint": bool(first and second) and not bool(set(first) & set(second)),
            "boundary_matches": len(first) == 100
            and len(second) >= 20
            and boundary == first[90:] + second[:20],
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (UsdbError, ValueError):
        print("Pagination check failed; no page or credential details printed.")
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Check cancelled.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
