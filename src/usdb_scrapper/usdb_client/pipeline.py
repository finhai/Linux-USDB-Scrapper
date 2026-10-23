"""Search orchestration with video filtering exclusively at the final stage."""

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from typing import Protocol

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.usdb_client.details import SongDetails, youtube_url
from usdb_scrapper.usdb_client.results import merge_song_results
from usdb_scrapper.usdb_client.search import SearchQuery
from usdb_scrapper.usdb_client.session import UsdbError


class PipelineError(UsdbError):
    """A pipeline dependency returned inconsistent data."""


class SearchSource(Protocol):
    def search(self, query: SearchQuery, *, max_pages: int = 100) -> tuple[SongEntry, ...]: ...


class DetailSource(Protocol):
    def fetch(self, song_id: int) -> SongDetails: ...


def filter_video_results(entries: Iterable[SongEntry]) -> tuple[SongEntry, ...]:
    """Keep supported video references, without claiming remote playability."""
    return tuple(entry for entry in entries if entry.youtube_url and youtube_url(entry.youtube_url))


@dataclass(frozen=True)
class SearchStages:
    retrieved: tuple[SongEntry, ...]
    enriched: tuple[SongEntry, ...]
    deduplicated: tuple[SongEntry, ...]
    output: tuple[SongEntry, ...]


class SearchPipeline:
    """Synchronous worker-only pipeline; no incomplete success on source errors.

    Each source retains its server order. Across sources first encounter wins;
    this is not a global resort. Details are cached only within one run, and the
    first supported video in comment encounter order is selected deterministically.
    That selection is not a relevance/availability judgment.
    """

    def __init__(
        self,
        search: SearchSource,
        details: DetailSource,
        *,
        pause: Callable[[float], None] = time.sleep,
    ) -> None:
        self._search = search
        self._details = details
        self._pause = pause

    def retrieve(
        self, queries: Iterable[SearchQuery], *, max_pages: int = 100
    ) -> tuple[SongEntry, ...]:
        """Fully paginate each query without filtering or deduplicating."""
        records: list[SongEntry] = []
        for index, query in enumerate(queries):
            if index:
                self._pause(1.0)
            records.extend(self._search.search(query, max_pages=max_pages))
        return tuple(records)

    def enrich(self, entries: Iterable[SongEntry]) -> tuple[SongEntry, ...]:
        """Retain every occurrence, including records with no video reference."""
        cache: dict[int, str | None] = {}
        result: list[SongEntry] = []
        for entry in entries:
            if entry.song_id not in cache:
                if cache:
                    self._pause(1.0)
                details = self._details.fetch(entry.song_id)
                if details.song_id != entry.song_id:
                    raise PipelineError("Detail response belongs to another song")
                candidates = (youtube_url(value) for value in details.youtube_urls)
                cache[entry.song_id] = next((value for value in candidates if value), None)
            result.append(replace(entry, youtube_url=cache[entry.song_id]))
        return tuple(result)

    def run(self, *queries: SearchQuery, max_pages: int = 100) -> SearchStages:
        retrieved = self.retrieve(queries, max_pages=max_pages)
        enriched = self.enrich(retrieved)
        deduplicated = merge_song_results(enriched)
        return SearchStages(retrieved, enriched, deduplicated, filter_video_results(deduplicated))
