"""Inspect the authenticated TXT entry page without exposing page contents."""

import json
import re
import sys
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from usdb_scrapper.credential_manager.terminal import get_credentials
from usdb_scrapper.usdb_client import UsdbError, UsdbSession


def safe_name(value):
    return value if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9-]{0,39}", value) else "[redacted]"


def target(value):
    try:
        url = urlsplit(urljoin("https://usdb.animux.de/", value))
        query = parse_qs(url.query)
        return {
            "same_origin": url.scheme == "https" and url.netloc == "usdb.animux.de",
            "route": [safe_name(v) for v in query.get("link", [])],
            "query_names": sorted(safe_name(k) for k in query),
        }
    except ValueError:
        return {"invalid": True}


class TxtStructure(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms = []
        self.form = None
        self.textareas = 0
        self.scripts = []
        self.script = None
        self.refresh_seconds = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.form = {
                "method": safe_name(attrs.get("method", "get").lower()),
                "target": target(attrs.get("action", "")),
                "fields": [],
            }
            self.forms.append(self.form)
        if tag in ("input", "button", "select") and self.form is not None:
            self.form["fields"].append(
                {
                    "name": safe_name(attrs.get("name", "")),
                    "type": safe_name(attrs.get("type", tag)),
                }
            )
        if tag == "textarea":
            self.textareas += 1
        if tag == "script":
            self.script = []
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            match = re.match(r"\s*(\d+)", attrs.get("content", ""))
            if match:
                self.refresh_seconds.append(int(match[1]))

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)

    def handle_endtag(self, tag):
        if tag == "form":
            self.form = None
        if tag == "script" and self.script is not None:
            self.scripts.append("".join(self.script))
            self.script = None

    def summary(self):
        script = "\n".join(self.scripts)
        return {
            "forms": self.forms,
            "textarea_count": self.textareas,
            "refresh_seconds": self.refresh_seconds,
            "timer_delay_candidates_ms": [
                int(v)
                for v in re.findall(r"set(?:Timeout|Interval)\s*\([^;]*?,\s*(\d+)\s*\)", script)
            ],
            "numeric_script_assignments": [
                {"name": name, "number": int(value)}
                for name, value in re.findall(
                    r"\b([A-Za-z_][A-Za-z_0-9]{0,39})\s*=\s*(\d{1,6})\s*;", script
                )
                if any(word in name.lower() for word in ("time", "count", "wait", "sec"))
            ],
            "script_submits_form": bool(re.search(r"\.submit\s*\(", script)),
        }


def main():
    if not sys.stdin.isatty():
        print("Run in your own terminal; do not pipe credentials.")
        return 2
    try:
        username, password = get_credentials()
        with UsdbSession() as session:
            session.login(username, password)
            username = password = ""
            page = session.get_html("/?link=gettxt&id=3289")
            print(json.dumps(TxtStructure(page).summary(), indent=2))
        return 0
    except (UsdbError, ValueError):
        print("TXT probe failed; no page or credential details printed.")
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Probe cancelled.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
