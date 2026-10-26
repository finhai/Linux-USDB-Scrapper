"""Verified USDB search request protocol and UI-independent sort state."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class SortField(StrEnum):
    ID = "id"
    ARTIST = "interpret"
    TITLE = "title"
    GENRE = "genre"
    YEAR = "year"
    EDITION = "edition"
    GOLDEN_NOTES = "golden"
    LANGUAGE = "language"
    CREATOR = "autor"
    RATING = "rating"
    VIEWS = "views"
    LAST_CHANGED = "lastchange"


class SortDirection(StrEnum):
    ASCENDING = "asc"
    DESCENDING = "desc"


@dataclass(frozen=True)
class SortState:
    """First/new field selection ascends; repeated selection toggles."""

    field: SortField | None = None
    direction: SortDirection = SortDirection.ASCENDING

    def __post_init__(self) -> None:
        if self.field is not None and not isinstance(self.field, SortField):
            raise TypeError("field must be a SortField or None")
        if not isinstance(self.direction, SortDirection):
            raise TypeError("direction must be a SortDirection")
        if self.field is None and self.direction != SortDirection.ASCENDING:
            raise ValueError("Unselected sort must start ascending")

    def select(self, field: SortField) -> "SortState":
        if not isinstance(field, SortField):
            raise TypeError("field must be a SortField")
        direction = SortDirection.ASCENDING
        if field == self.field and self.direction == SortDirection.ASCENDING:
            direction = SortDirection.DESCENDING
        return SortState(field, direction)


@dataclass(frozen=True)
class SearchQuery:
    artist: str = ""
    title: str = ""
    sort: SortState = SortState()

    def __post_init__(self) -> None:
        if not isinstance(self.artist, str) or not isinstance(self.title, str):
            raise TypeError("Artist and title must be strings")
        if not isinstance(self.sort, SortState):
            raise TypeError("sort must be a SortState")
        if not self.artist.strip() and not self.title.strip():
            raise ValueError("Provide an artist or title")

    def form_fields(self) -> dict[str, str]:
        """Preserve query text; always send both fields and explicit sort/page."""
        return {
            "details": "1",
            "interpret": self.artist,
            "title": self.title,
            "start": "0",
            "order": (self.sort.field or SortField.ID).value,
            "ud": self.sort.direction.value,
        }


class SearchTransport(Protocol):
    def post_html(self, path: str, fields: Mapping[str, str]) -> str: ...


class SearchClient:
    """First-page HTML retrieval; parsing and pagination belong to later work.

    Accepts UsdbSession through its public API, including its authentication errors.
    Call from a worker, not the Qt event thread. Never log returned HTML.
    """

    def __init__(self, session: SearchTransport) -> None:
        self._session = session

    def search_html(self, query: SearchQuery) -> str:
        if not isinstance(query, SearchQuery):
            raise TypeError("query must be a SearchQuery")
        return self._session.post_html("/?link=list", query.form_fields())
