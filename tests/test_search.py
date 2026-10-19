"""Search protocol and sort transitions, independent of live credentials."""

import pytest

from usdb_scrapper.usdb_client.search import (
    SearchClient,
    SearchQuery,
    SortDirection,
    SortField,
    SortState,
)
from usdb_scrapper.usdb_client.session import AuthenticationError


@pytest.mark.parametrize("field", list(SortField))
def test_first_selection_reselection_and_switch(field):
    original = SortState()
    first = original.select(field)
    assert first == SortState(field, SortDirection.ASCENDING)
    second = first.select(field)
    assert second.direction == SortDirection.DESCENDING
    assert second.select(field) == first
    other = SortField.TITLE if field != SortField.TITLE else SortField.ARTIST
    assert second.select(other) == SortState(other, SortDirection.ASCENDING)
    assert original.field is None


@pytest.mark.parametrize(
    "artist,title", [("ABBA", ""), ("", "Dancing Queen"), ("ABBA", "Dancing Queen")]
)
def test_search_always_sends_both_filters_and_explicit_sort(artist, title):
    assert SearchQuery(artist, title).form_fields() == {
        "details": "1",
        "interpret": artist,
        "title": title,
        "start": "0",
        "order": "id",
        "ud": "asc",
    }


def test_search_preserves_text_and_uses_verified_wire_names():
    query = SearchQuery(
        " B.o.B ", "Dón't Stop", SortState(SortField.CREATOR, SortDirection.DESCENDING)
    )
    assert query.form_fields()["interpret"] == " B.o.B "
    assert query.form_fields()["title"] == "Dón't Stop"
    assert query.form_fields()["order"] == "autor"
    assert query.form_fields()["ud"] == "desc"


def test_client_returns_server_order_without_local_sorting():
    class Session:
        def post_html(self, path, fields):
            assert path == "/?link=list"
            assert fields["order"] == "id" and fields["ud"] == "desc"
            return '<a href="?link=detail&id=9">Nine</a><a href="?link=detail&id=2">Two</a>'

    result = SearchClient(Session()).search_html(
        SearchQuery(title="example", sort=SortState(SortField.ID, SortDirection.DESCENDING))
    )
    assert result.index("id=9") < result.index("id=2")


def test_authentication_error_propagates():
    class Session:
        def post_html(self, path, fields):
            raise AuthenticationError("Login required")

    with pytest.raises(AuthenticationError):
        SearchClient(Session()).search_html(SearchQuery(title="example"))


@pytest.mark.parametrize("artist,title", [("", ""), (" ", "\t")])
def test_blank_search_rejected(artist, title):
    with pytest.raises(ValueError):
        SearchQuery(artist, title)


def test_invalid_sort_types_rejected():
    with pytest.raises(TypeError):
        SortState().select("title")
    with pytest.raises(TypeError):
        SortState("title")
    with pytest.raises(TypeError):
        SortState(direction="desc")
    with pytest.raises(ValueError):
        SortState(direction=SortDirection.DESCENDING)
