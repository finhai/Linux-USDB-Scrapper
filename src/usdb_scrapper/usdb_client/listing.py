"""Parse the observed detailed listing and traverse 100-result pages."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.usdb_client.search import SearchQuery, SearchTransport
from usdb_scrapper.usdb_client.session import UsdbError


class ListingParseError(UsdbError):
    """The response cannot safely be interpreted as a detailed song listing."""


class PaginationError(UsdbError):
    """Traversal overlapped, exceeded its bound, or returned too many records."""


@dataclass
class _Cell:
    text: list[str] = field(default_factory=list)
    ids: list[int] = field(default_factory=list)

    def value(self) -> str:
        return " ".join("".join(self.text).split())


@dataclass
class _Row:
    cells: list[_Cell] = field(default_factory=list)
    current: _Cell | None = None
    nested: bool = False


class _ListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[_Row] = []
        self.rows: list[_Row] = []
        self.fields: set[str] = set()
        self.detail_links = 0
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in ("script", "style"):
            self.ignored += 1
        if tag in ("input", "select"):
            self.fields.add(values.get("name") or "")
        if tag == "tr":
            if self.stack:
                self.stack[-1].nested = True
            self.stack.append(_Row())
        if tag in ("td", "th") and self.stack:
            row = self.stack[-1]
            row.current = _Cell()
            row.cells.append(row.current)
        if tag == "br" and self.stack and self.stack[-1].current is not None:
            self.stack[-1].current.text.append(" ")
        if tag != "a":
            return
        try:
            url = urlsplit(urljoin("https://usdb.animux.de/", values.get("href") or ""))
        except ValueError:
            raise ListingParseError("Malformed listing link") from None
        if url.scheme != "https" or url.netloc != "usdb.animux.de":
            return
        query = parse_qs(url.query)
        if query.get("link") != ["detail"]:
            return
        self.detail_links += 1
        ids = query.get("id", [])
        if len(ids) != 1 or not ids[0].isascii() or not ids[0].isdigit() or int(ids[0]) < 1:
            raise ListingParseError("Invalid song identifier")
        if not self.stack or self.stack[-1].current is None:
            raise ListingParseError("Song link outside a recognized row")
        self.stack[-1].current.ids.append(int(ids[0]))

    def handle_data(self, data: str) -> None:
        if not self.ignored and self.stack and self.stack[-1].current is not None:
            self.stack[-1].current.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self.ignored = max(0, self.ignored - 1)
        if tag in ("td", "th") and self.stack:
            self.stack[-1].current = None
        if tag == "tr" and self.stack:
            row = self.stack.pop()
            if not row.nested and any(cell.ids for cell in row.cells):
                self.rows.append(row)


def _number(value: str) -> int | None:
    if not value:
        return None
    if not value.isascii() or not value.isdigit():
        raise ListingParseError("Unexpected numeric song metadata")
    return int(value)


def parse_listing(html: str) -> tuple[SongEntry, ...]:
    """Reject changed rows rather than silently dropping songs or shifting columns."""
    parser = _ListingParser()
    parser.feed(html)
    parser.close()
    if parser.stack:
        raise ListingParseError("Unclosed listing rows")
    if not {"interpret", "title", "details", "limit", "order", "ud"} <= parser.fields:
        raise ListingParseError("Expected detailed listing controls")
    entries: list[SongEntry] = []
    seen: set[int] = set()
    parsed_links = 0
    for row in parser.rows:
        if len(row.cells) != 13:
            raise ListingParseError("Detailed listing column layout changed")
        ids = {song_id for cell in row.cells for song_id in cell.ids}
        title_ids = set(row.cells[3].ids)
        if len(ids) != 1 or title_ids != ids:
            raise ListingParseError("Ambiguous song row")
        song_id = next(iter(ids))
        if song_id in seen:
            raise ListingParseError("Duplicate song row")
        seen.add(song_id)
        parsed_links += sum(len(cell.ids) for cell in row.cells)
        text = [cell.value() for cell in row.cells]
        if text[7] not in ("", "Yes", "No"):
            raise ListingParseError("Unexpected golden-note value")
        try:
            entries.append(
                SongEntry(
                    song_id=song_id,
                    artist=text[2],
                    title=text[3],
                    genre=text[4] or None,
                    year=_number(text[5]),
                    edition=text[6] or None,
                    golden_notes={"": None, "Yes": True, "No": False}[text[7]],
                    language=text[8] or None,
                    creator=text[9] or None,
                    views=_number(text[11]),
                )
            )
        except (ValueError, TypeError):
            raise ListingParseError("Invalid song metadata") from None
    if parsed_links != parser.detail_links:
        raise ListingParseError("Some song links were outside recognized rows")
    return tuple(entries)


class PagedSearchClient:
    """Collect complete results or raise; never silently return a truncated result.

    Uses fixed 100-result pages and preserves the query's server sort order.
    Server changes during traversal can invalidate offset pagination; overlap is
    detected, but the server provides no snapshot guarantee against omissions.
    """

    def __init__(
        self, session: SearchTransport, *, pause: Callable[[float], None] = time.sleep
    ) -> None:
        self._session = session
        self._pause = pause

    def search(self, query: SearchQuery, *, max_pages: int = 100) -> tuple[SongEntry, ...]:
        if not isinstance(query, SearchQuery):
            raise TypeError("query must be a SearchQuery")
        if type(max_pages) is not int or max_pages < 1:
            raise ValueError("max_pages must be a positive integer")
        result: list[SongEntry] = []
        seen: set[int] = set()
        for page in range(max_pages):
            if page:
                self._pause(1.0)
            fields = {**query.form_fields(), "start": str(page * 100), "limit": "100"}
            entries = parse_listing(self._session.post_html("/?link=list", fields))
            if len(entries) > 100:
                raise PaginationError("Server returned more than the requested page size")
            ids = {entry.song_id for entry in entries}
            if seen & ids:
                raise PaginationError("Search pages overlap; restart the search")
            seen.update(ids)
            result.extend(entries)
            if len(entries) < 100:
                return tuple(result)
        raise PaginationError("Search exceeded the configured page limit")
