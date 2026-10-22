import pytest

from usdb_scrapper.normalization.search import normalize_search_input


@pytest.mark.parametrize(
    "source,expected",
    [
        ("  Dancing  Queen ", "dancing queen"),
        ("Don't Stop", "don't stop"),
        ("Dont Stop", "dont stop"),
        ("dont stop", "dont stop"),
        ("Dónt Stóp", "dónt stóp"),
        ("Do\u0301nt\tSto\u0301p", "dónt stóp"),
    ],
)
def test_preserves_semantic_distinctions(source, expected):
    assert normalize_search_input(source) == expected
