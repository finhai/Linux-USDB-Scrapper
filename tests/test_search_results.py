from dataclasses import replace

import pytest

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.usdb_client.results import merge_song_results


def song(song_id, artist="Artist", title="Title"):
    return SongEntry(song_id=song_id, artist=artist, title=title)


def test_overlapping_artist_and_title_search_paths_surface_song_once():
    shared = song(3289, "ABBA", "Dancing Queen")
    artist_results = [song(9), shared, song(37)]
    title_results = [song(876), replace(shared), song(4609)]
    result = merge_song_results(artist_results, title_results)
    assert [entry.song_id for entry in result] == [9, 3289, 37, 876, 4609]
    assert result[1] is shared
    assert len(artist_results) == 3 and len(title_results) == 3


def test_same_text_different_ids_remain_distinct():
    assert [entry.song_id for entry in merge_song_results([song(1), song(2)])] == [1, 2]


def test_same_id_different_metadata_keeps_first_record_intact():
    first = song(1, "Original", "Original title")
    later = replace(first, artist="Changed", youtube_url="https://youtu.be/xFrGuyw1V8s")
    result = merge_song_results([first], [later])
    assert result == (first,)
    assert result[0] is first
    assert result[0].youtube_url is None  # Not a filter or field-level enrichment merge.


def test_duplicates_within_source_and_multiple_one_shot_sources():
    first = song(3)
    result = merge_song_results(iter([first, first]), (), (song(i) for i in [2, 3, 1]))
    assert [entry.song_id for entry in result] == [3, 2, 1]


def test_empty_inputs():
    assert merge_song_results() == ()
    assert merge_song_results([], iter(())) == ()


def test_later_source_failure_propagates_without_partial_success():
    def failing():
        yield song(2)
        raise RuntimeError("source failed")

    with pytest.raises(RuntimeError, match="source failed"):
        merge_song_results([song(1)], failing())


def test_invalid_record_is_not_silently_ignored():
    with pytest.raises(TypeError, match="SongEntry"):
        merge_song_results([song(1)], [None])
