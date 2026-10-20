"""Combine search paths without confusing song identity with display metadata."""

from collections.abc import Iterable

from usdb_scrapper.domain import SongEntry


def merge_song_results(*sources: Iterable[SongEntry]) -> tuple[SongEntry, ...]:
    """Return one record per Song ID, in source/encounter order.

    The first record wins intact when later sources disagree about metadata.
    Callers should order sources by preference; this function neither merges
    fields nor filters songs lacking a YouTube reference. It consumes every
    source before returning, so a later source error cannot look like success.
    """
    seen: set[int] = set()
    result: list[SongEntry] = []
    for source in sources:
        for entry in source:
            if not isinstance(entry, SongEntry):
                raise TypeError("Search results must contain SongEntry records")
            if entry.song_id not in seen:
                seen.add(entry.song_id)
                result.append(entry)
    return tuple(result)
