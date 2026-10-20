import pytest

from usdb_scrapper.usdb_client.listing import (
    ListingParseError,
    PagedSearchClient,
    PaginationError,
    parse_listing,
)
from usdb_scrapper.usdb_client.search import SearchQuery
from usdb_scrapper.usdb_client.session import AuthenticationError

CONTROLS = "".join(
    f'<input name="{name}">' for name in ("interpret", "title", "details", "limit", "order", "ud")
)


def row(song_id):
    return (
        "<tr>"
        + "".join(
            f"<td>{cell}</td>"
            for cell in [
                "",
                "<img>",
                "Synthetic Artist",
                f'<a href="?link=detail&id={song_id}">Title &amp; Love</a>',
                "",
                "2004",
                "",
                "No",
                "English",
                "Creator",
                "<img><img>",
                "647",
                "<img>",
            ]
        )
        + "</tr>"
    )


def page(ids):
    return (
        CONTROLS
        + "<table><tr><td><table>"
        + "".join(row(i) for i in ids)
        + "</table></td></tr></table>"
    )


def test_observed_column_mapping_and_unknown_image_metadata():
    (entry,) = parse_listing(page([9]))
    assert (entry.song_id, entry.artist, entry.title) == (9, "Synthetic Artist", "Title & Love")
    assert entry.year == 2004 and entry.views == 647
    assert entry.golden_notes is False and entry.genre is None
    assert entry.creator == "Creator" and entry.language == "English"
    assert entry.rating is None and entry.date is None and entry.last_modified is None


@pytest.mark.parametrize(
    "html",
    [
        "<p>Unexpected response</p>",
        page([1]).replace("<td>2004</td>", ""),
        page([1]).replace("2004", "unknown-year"),
        page([1]).replace(">No<", ">unknown<"),
        page([1, 1]),
        page([1]).replace("id=1", "id=invalid"),
        page([1]).replace("Synthetic Artist", " "),
        CONTROLS + '<a href="?link=detail&id=1">Outside row</a>',
    ],
)
def test_invalid_pages_fail_instead_of_dropping_records(html):
    with pytest.raises(ListingParseError):
        parse_listing(html)


def test_recognized_empty_listing():
    assert parse_listing(page([])) == ()


class Session:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.calls = []

    def post_html(self, path, fields):
        self.calls.append((path, fields))
        response = next(self.pages)
        if isinstance(response, Exception):
            raise response
        return response


def test_more_than_100_results_preserve_order_and_filters():
    session = Session([page(range(1, 101)), page(range(101, 138))])
    pauses = []
    result = PagedSearchClient(session, pause=pauses.append).search(SearchQuery(title="Love"))
    assert [item.song_id for item in result] == list(range(1, 138))
    assert [call[1]["start"] for call in session.calls] == ["0", "100"]
    assert all(call[1]["limit"] == "100" and call[1]["title"] == "Love" for call in session.calls)
    assert pauses == [1.0]


def test_exact_page_multiple_requires_empty_terminal_page():
    session = Session([page(range(1, 101)), page([])])
    assert (
        len(PagedSearchClient(session, pause=lambda _: None).search(SearchQuery(title="Love")))
        == 100
    )
    assert len(session.calls) == 2


@pytest.mark.parametrize(
    "second,error",
    [
        (page(range(50, 80)), PaginationError),
        ("<p>Layout changed</p>", ListingParseError),
        (AuthenticationError("Login required"), AuthenticationError),
    ],
)
def test_failed_later_page_never_returns_partial_success(second, error):
    session = Session([page(range(1, 101)), second])
    with pytest.raises(error):
        PagedSearchClient(session, pause=lambda _: None).search(SearchQuery(title="Love"))


def test_bound_prevents_infinite_traversal():
    session = Session([page(range(1, 101))])
    with pytest.raises(PaginationError, match="limit"):
        PagedSearchClient(session).search(SearchQuery(title="Love"), max_pages=1)


def test_oversized_page_rejected():
    with pytest.raises(PaginationError):
        PagedSearchClient(Session([page(range(1, 102))])).search(SearchQuery(title="Love"))
