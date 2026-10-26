"""Bounded TXT wait-page retrieval; content decoding belongs to the next stage."""

import re
import time
from collections.abc import Callable, Mapping
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import parse_qs, urljoin, urlsplit

from usdb_scrapper.usdb_client.content import extract_txt
from usdb_scrapper.usdb_client.session import UsdbError


class TxtRetrievalError(UsdbError):
    """The TXT request sequence did not match the supported protocol."""


class TxtSession(Protocol):
    def get_html(self, path: str) -> str: ...
    def post_html(self, path: str, fields: Mapping[str, str]) -> str: ...


class _Page(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__()
        self.forms: list[tuple[dict[str, str | None], list[dict[str, str | None]]]] = []
        self.current: list[dict[str, str | None]] | None = None
        self.scripts: list[str] = []
        self.in_script = False
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "form":
            self.current = []
            self.forms.append((values, self.current))
        elif tag == "input" and self.current is not None:
            self.current.append(values)
        elif tag == "script":
            self.in_script = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.current = None
        elif tag == "script":
            self.in_script = False

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.scripts.append(data)


def _wait_form(html: str, song_id: int) -> tuple[str, dict[str, str], float]:
    page = _Page(html)
    forms = [
        (attrs, inputs)
        for attrs, inputs in page.forms
        if any(item.get("name") == "wd" for item in inputs)
    ]
    if len(forms) != 1:
        raise TxtRetrievalError("Expected one TXT wait form")
    attrs, inputs = forms[0]
    path = f"/?link=gettxt&id={song_id}"
    try:
        url = urlsplit(urljoin("https://usdb.animux.de" + path, attrs.get("action") or ""))
        query = parse_qs(url.query)
    except ValueError:
        raise TxtRetrievalError("Invalid TXT form destination") from None
    if (
        url.scheme != "https"
        or url.netloc != "usdb.animux.de"
        or url.path != "/"
        or url.fragment
        or query != {"link": ["gettxt"], "id": [str(song_id)]}
        or (attrs.get("method") or "").lower() != "post"
    ):
        raise TxtRetrievalError("Unexpected TXT form destination or method")
    fields: dict[str, str] = {}
    for item in inputs:
        name = item.get("name")
        if "disabled" in item:
            continue
        if not name or name in fields or (item.get("type") or "").lower() != "hidden":
            raise TxtRetrievalError("Unexpected TXT form controls")
        fields[name] = item.get("value") or ""
    if not fields.get("wd"):
        raise TxtRetrievalError("Missing TXT wait field")
    script = "\n".join(page.scripts)
    times = re.findall(r"\btime\s*=\s*(\d+)\s*;", script)
    delays = re.findall(r"set(?:Timeout|Interval)\s*\([^;]*?,\s*(\d+)\s*\)", script)
    if (
        len(times) != 1
        or not 0 <= int(times[0]) <= 120
        or not delays
        or any(int(delay) != 1000 for delay in delays)
        or not re.search(r"\.submit\s*\(\s*\)", script)
    ):
        raise TxtRetrievalError("Unrecognized TXT countdown")
    # Include the terminal tick, conservatively waiting beyond the displayed count.
    return path, fields, float(int(times[0]) + 1)


class TxtClient:
    """Worker-only GET, wait, POST sequence. Never executes page JavaScript.

    Returns the final response HTML for separate extraction/decoding. A returned
    page does not by itself prove valid UltraStar content. No automatic retries.
    """

    def __init__(self, session: TxtSession, *, pause: Callable[[float], None] = time.sleep):
        self._session = session
        self._pause = pause

    def retrieve_page(self, song_id: int) -> str:
        if isinstance(song_id, bool) or not isinstance(song_id, int) or song_id <= 0:
            raise ValueError("Song ID must be a positive integer")
        page = self._session.get_html(f"/?link=gettxt&id={song_id}")
        path, fields, seconds = _wait_form(page, song_id)
        try:
            self._pause(seconds)
            result = self._session.post_html(path, fields)
        finally:
            fields.clear()
        if not result.strip() or any(
            item.get("name") == "wd" for _, inputs in _Page(result).forms for item in inputs
        ):
            raise TxtRetrievalError("TXT follow-up returned an empty page or another wait form")
        return result

    def retrieve_text(self, song_id: int) -> str:
        """Retrieve and extract raw TXT; song metadata is not interpreted here."""
        return extract_txt(self.retrieve_page(song_id))
