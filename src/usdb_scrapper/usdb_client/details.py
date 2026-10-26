"""Song-detail comment extraction, independent of cover retrieval."""

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import parse_qs, urljoin, urlsplit

from usdb_scrapper.usdb_client.session import UsdbError

_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
_URL = re.compile(r"https?://[^\s<>\[\]\"']+")


class DetailParseError(UsdbError):
    """The requested song/comments structure could not be verified."""


def _song_id(value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError("song_id must be a positive integer")


def youtube_url(value: str) -> str | None:
    """Normalize a supported video reference, without fetching the video."""
    try:
        url = urlsplit(value.strip().rstrip(".,;!)"))
        if url.scheme not in ("https", "http") or url.username or url.password or url.port:
            return None
        host = url.hostname
        parts = url.path.strip("/").split("/")
        if host == "youtu.be" and len(parts) == 1:
            video = parts[0]
        elif host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if url.path == "/watch":
                values = parse_qs(url.query).get("v", [])
                if len(values) != 1:
                    return None
                video = values[0]
            elif len(parts) == 2 and parts[0] in ("embed", "shorts", "live"):
                video = parts[1]
            else:
                return None
        elif host in ("youtube-nocookie.com", "www.youtube-nocookie.com"):
            if len(parts) != 2 or parts[0] != "embed":
                return None
            video = parts[1]
        else:
            return None
    except ValueError:
        return None
    return f"https://www.youtube.com/watch?v={video}" if _VIDEO_ID.fullmatch(video) else None


@dataclass(frozen=True)
class SongDetails:
    song_id: int
    youtube_urls: tuple[str, ...]


class _Comments(HTMLParser):
    def __init__(self, song_id: int) -> None:
        super().__init__()
        self.song_id = song_id
        self.identified = False
        self.depth = 0
        self.comment_depth: int | None = None
        self.found_comments = False
        self.ended_comments = False
        self.row_class = ""
        self.cell_text: list[str] = []
        self.suppressed = 0
        self.urls: list[str] = []

    def add(self, value: str) -> None:
        normalized = youtube_url(value)
        if normalized and normalized not in self.urls:
            self.urls.append(normalized)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "table":
            self.depth += 1
        if tag == "tr":
            self.row_class = values.get("class") or ""
        if tag in ("td", "th"):
            self.cell_text = []
        if tag == "form":
            try:
                url = urlsplit(urljoin("https://usdb.animux.de/", values.get("action") or ""))
                query = parse_qs(url.query)
                if (
                    url.scheme == "https"
                    and url.netloc == "usdb.animux.de"
                    and query.get("link") == ["detail"]
                    and query.get("id") == [str(self.song_id)]
                ):
                    self.identified = True
            except ValueError:
                pass
        if tag in ("script", "style", "textarea", "form"):
            self.suppressed += 1
        if self.comment_depth is not None and not self.suppressed:
            if tag == "a":
                self.add(values.get("href") or "")
            elif tag in ("iframe", "embed"):
                self.add(values.get("src") or "")
            elif tag == "object":
                self.add(values.get("data") or "")

    def handle_data(self, data: str) -> None:
        if not self.suppressed:
            self.cell_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "textarea", "form"):
            self.suppressed = max(0, self.suppressed - 1)
        if tag in ("td", "th"):
            text = "".join(self.cell_text)
            if self.row_class == "list_head" and text.strip() == "Comments by users (two cents)":
                self.comment_depth = self.depth
                self.found_comments = True
            elif self.row_class == "list_tr2" and text.strip() == "Write Comment":
                self.comment_depth = None
                self.ended_comments = True
            elif self.comment_depth is not None:
                for match in _URL.finditer(text):
                    self.add(match.group())
            self.cell_text = []
        if tag == "table":
            if self.comment_depth == self.depth:
                self.comment_depth = None
                self.ended_comments = True
            self.depth -= 1


def parse_song_details(html: str, song_id: int) -> SongDetails:
    _song_id(song_id)
    parser = _Comments(song_id)
    parser.feed(html)
    parser.close()
    if not parser.identified or not parser.found_comments or not parser.ended_comments:
        raise DetailParseError("Song detail/comments structure could not be verified")
    return SongDetails(song_id, tuple(parser.urls))


class DetailTransport(Protocol):
    def get_html(self, path: str) -> str: ...


class DetailClient:
    def __init__(self, session: DetailTransport) -> None:
        self._session = session

    def fetch(self, song_id: int) -> SongDetails:
        _song_id(song_id)
        return parse_song_details(self._session.get_html(f"/?link=detail&id={song_id}"), song_id)
