"""Sanitized discovery fixtures; no network or credentials required."""

import runpy
from pathlib import Path

SearchSummary = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "probe_usdb_search.py"))[
    "SearchSummary"
]


def test_candidate_ids_are_ordered_unique_and_same_origin():
    result = SearchSummary("""
    <a href="?link=detail&id=42">song</a>
    <a href="?link=detail&id=7">song</a>
    <a href="?link=detail&id=42">duplicate</a>
    <a href="https://evil.example/?link=detail&id=8">external</a>
    <a href="?link=profile&id=9">profile</a>
    <a href="?link=detail&id=-1">invalid</a>
    <a href="?link=detail&id=0">invalid</a>
    """).summary()
    assert result["candidate_song_ids_in_page_order"] == [42, 7]
    assert result["candidate_song_count_on_page"] == 2


def test_only_allowlisted_metadata_is_reported():
    result = SearchSummary("""
    <input name="pass" value="secret-password">
    <input type="hidden" name="token" value="secret-token">
    <p>private account content</p>
    <select name="order"><option value="title">Song title</option></select>
    <select name="account"><option value="private-user">User</option></select>
    <a href="?link=list&order=title&direction=asc&token=secret-token">sort</a>
    """).summary()
    assert result["sort_option_values"] == {"order": ["title"]}
    assert result["sort_link_parameters"] == [{"order": ["title"], "direction": ["asc"]}]
    assert "secret" not in str(result)
    assert "private" not in str(result)


def test_missing_results_are_not_reported_as_a_total_count():
    result = SearchSummary("<p>Unrecognized layout</p>").summary()
    assert result["candidate_song_ids_in_page_order"] == []
    assert "total_count" not in result


def test_direction_controls_and_filter_echo_are_captured():
    result = SearchSummary("""
    <input name="interpret" value="ABBA"><input name="title" value="Don't Stop">
    <select name="ud"><option value="up">Ascending</option>
    <option value="down">Descending</option></select>
    <input name="ud" type="radio" value="up" checked>
    <input name="user" value="private-user">
    """).summary()
    assert result["sort_option_values"]["ud"] == ["up", "down"]
    assert result["direction_controls"] == [{"value": "up", "type": "radio", "checked": True}]
    assert result["echoed_search_filters"] == {"interpret": "ABBA", "title": "Don't Stop"}
    assert "private-user" not in str(result)


def test_query_payload_explicitly_clears_other_filter():
    module = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "probe_usdb_search.py"))
    fields = module["search_fields"]({"title": "Don't Stop"})
    assert fields["interpret"] == ""
    assert fields["title"] == "Don't Stop"
    assert fields["start"] == "0"
