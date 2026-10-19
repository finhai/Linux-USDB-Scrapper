"""Synthetic discovery checks; never contact USDB."""

import runpy
from pathlib import Path

ListingStructure = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "probe_usdb_pagination.py")
)["ListingStructure"]


def test_nested_layout_and_account_controls_are_excluded():
    result = ListingStructure("""<table><tr><td>private account
    <input name="pass" value="secret"><table>
    <tr><td>Artist</td><td><a href="?link=detail&id=42">Title</a></td>
    <td><img alt="golden" src="private-url"></td></tr>
    </table></td></tr></table>""").summary()
    assert result["candidate_ids"] == [42]
    assert result["sample_rows"][0]["cells"][0]["text"] == "Artist"
    assert result["sample_rows"][0]["cells"][1]["song_ids"] == [42]
    assert "private" not in str(result)
    assert "secret" not in str(result)


def test_order_and_duplicate_evidence_are_preserved():
    result = ListingStructure("""<tr><td><a href="?link=detail&id=8">A</a>
    <a href="?link=detail&id=8">A</a></td></tr>
    <tr><td><a href="?link=detail&id=8">Duplicate row</a></td></tr>
    <tr><td><a href="https://evil.example/?link=detail&id=1">External</a></td></tr>
    """).summary()
    assert result["candidate_ids"] == [8, 8]
    assert result["duplicate_ids"]


def test_header_positions_and_numeric_page_controls():
    result = ListingStructure("""<tr><th>Check</th>
    <th><a href="?link=list&order=interpret">Artist</a></th></tr>
    <a href="?link=list&start=100&limit=100&token=secret">Next</a>
    <a href="?link=list&start=private">Bad</a>""").summary()
    assert result["sort_header_cells"] == [[{"cell": 1, "order": "interpret"}]]
    assert result["page_controls"] == [{"start": ["100"], "limit": ["100"]}]
    assert "secret" not in str(result)
