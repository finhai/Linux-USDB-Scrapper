import pytest

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.usdb_client.details import SongDetails
from usdb_scrapper.usdb_client.pipeline import PipelineError, SearchPipeline, filter_video_results
from usdb_scrapper.usdb_client.search import SearchQuery
from usdb_scrapper.usdb_client.session import TransportError

URL = "https://www.youtube.com/watch?v=xFrGuyw1V8s"


def song(song_id):
    return SongEntry(song_id=song_id, artist="Artist", title="Title")


class Search:
    def __init__(self, events):
        self.events = events

    def search(self, query, *, max_pages=100):
        self.events.append(("search", query.artist, query.title, max_pages))
        return (song(1), song(2)) if query.artist else (song(2), song(3))


class Details:
    def __init__(self, events):
        self.events = events

    def fetch(self, song_id):
        self.events.append(("detail", song_id))
        return SongDetails(song_id, (URL,) if song_id != 1 else ())


def test_only_final_output_is_filtered_after_all_pages_details_and_dedup():
    events = []
    stages = SearchPipeline(Search(events), Details(events), pause=lambda _: None).run(
        SearchQuery(artist="Artist"), SearchQuery(title="Title"), max_pages=4
    )
    assert [e.song_id for e in stages.retrieved] == [1, 2, 2, 3]
    assert all(e.youtube_url is None for e in stages.retrieved)
    assert [e.song_id for e in stages.enriched] == [1, 2, 2, 3]
    assert stages.enriched[0].youtube_url is None
    assert stages.enriched[1].youtube_url == URL
    assert [e.song_id for e in stages.deduplicated] == [1, 2, 3]
    assert [e.song_id for e in stages.output] == [2, 3]
    assert events == [
        ("search", "Artist", "", 4),
        ("search", "", "Title", 4),
        ("detail", 1),
        ("detail", 2),
        ("detail", 3),
    ]


def test_stages_can_be_called_independently_and_cache_is_per_run():
    events = []
    pipeline = SearchPipeline(Search(events), Details(events), pause=lambda _: None)
    records = pipeline.retrieve([SearchQuery(artist="Artist")])
    assert not any(e[0] == "detail" for e in events)
    enriched = pipeline.enrich(records)
    assert len(enriched) == 2
    pipeline.enrich(records)
    assert events.count(("detail", 1)) == 2
    assert len(filter_video_results(enriched)) == 1


def test_detail_failure_does_not_become_absence_or_partial_success():
    class Failing:
        def fetch(self, song_id):
            raise TransportError("failed")

    with pytest.raises(TransportError):
        SearchPipeline(Search([]), Failing()).run(SearchQuery(artist="Artist"))


def test_wrong_song_response_rejected():
    class Wrong:
        def fetch(self, song_id):
            return SongDetails(999, (URL,))

    with pytest.raises(PipelineError):
        SearchPipeline(Search([]), Wrong()).enrich([song(1)])


def test_multiple_candidates_choose_first_supported_video():
    class Multiple:
        def fetch(self, song_id):
            return SongDetails(
                song_id, ("https://youtube.com/channel/abc", URL, "https://youtu.be/abcdefghijk")
            )

    enriched = SearchPipeline(Search([]), Multiple()).enrich([song(1)])
    assert enriched[0].youtube_url == URL


def test_empty_input_never_calls_dependencies():
    events = []
    stages = SearchPipeline(Search(events), Details(events)).run()
    assert stages.output == stages.retrieved == stages.enriched == stages.deduplicated == ()
    assert events == []


def test_search_failure_prevents_detail_requests():
    events = []

    class Failing:
        def search(self, query, *, max_pages=100):
            raise TransportError("page failed")

    with pytest.raises(TransportError):
        SearchPipeline(Failing(), Details(events)).run(SearchQuery(title="Title"))
    assert events == []


def test_real_paginator_and_detail_parser_are_wired_before_final_filter():
    from test_details import document
    from test_listing import page

    from usdb_scrapper.usdb_client.details import DetailClient
    from usdb_scrapper.usdb_client.listing import PagedSearchClient

    class Transport:
        def __init__(self):
            self.events = []

        def post_html(self, path, fields):
            self.events.append(("page", fields["start"]))
            return page([3289, 9])

        def get_html(self, path):
            song_id = int(path.split("id=")[1])
            self.events.append(("detail", song_id))
            return document(URL if song_id == 3289 else "No video").replace(
                "id=3289", f"id={song_id}"
            )

    transport = Transport()
    pipeline = SearchPipeline(
        PagedSearchClient(transport, pause=lambda _: None),
        DetailClient(transport),
        pause=lambda _: None,
    )
    stages = pipeline.run(SearchQuery(artist="Artist"), SearchQuery(title="Title"))
    assert [entry.song_id for entry in stages.retrieved] == [3289, 9, 3289, 9]
    assert len(stages.enriched) == 4
    assert [entry.song_id for entry in stages.deduplicated] == [3289, 9]
    assert [entry.song_id for entry in stages.output] == [3289]
    assert transport.events == [("page", "0"), ("page", "0"), ("detail", 3289), ("detail", 9)]
