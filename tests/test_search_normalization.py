"""Policies are explicit; tests do not claim equivalence on the live server."""

from itertools import product

import pytest

from usdb_scrapper.normalization.search import (
    PunctuationMode,
    SearchNormalizationPolicy,
    normalize_search_input,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Don't Stop", "Don't Stop"),
        ("Dont Stop", "Dont Stop"),
        ("dont stop", "dont stop"),
        ("Dónt Stóp", "Dónt Stóp"),
        ("  Don’t\tStop\r\n", "Don’t Stop"),
        (" AC/DC ", "AC/DC"),
        ("B.o.B", "B.o.B"),
        ("  a\u00a0\u2003b  ", "a b"),
        ("Do\u0301nt Sto\u0301p", "Dónt Stóp"),
        ("", ""),
        (" \n\t", ""),
        ("東京 संगीत", "東京 संगीत"),
        ("C++ & Friends", "C++ & Friends"),
    ],
)
def test_default_preserves_case_accents_and_punctuation(value, expected):
    assert normalize_search_input(value) == expected


@pytest.mark.parametrize(
    "value", ["Don't Stop", "Dont Stop", "dont stop", "Dónt Stóp", "Don’t Stop"]
)
def test_explicit_lossy_policy_maps_research_examples(value):
    policy = SearchNormalizationPolicy(
        casefold=True, strip_diacritics=True, punctuation=PunctuationMode.REMOVE
    )
    assert normalize_search_input(value, policy=policy) == "dont stop"


@pytest.mark.parametrize(
    "value,policy,expected",
    [
        ("Straße", SearchNormalizationPolicy(casefold=True), "strasse"),
        ("Dónt Stóp", SearchNormalizationPolicy(strip_diacritics=True), "Dont Stop"),
        ("AC/DC", SearchNormalizationPolicy(punctuation=PunctuationMode.SPACE), "AC DC"),
        ("B.o.B", SearchNormalizationPolicy(punctuation=PunctuationMode.REMOVE), "BoB"),
        ("a—b…c", SearchNormalizationPolicy(punctuation=PunctuationMode.SPACE), "a b c"),
        ("!!!", SearchNormalizationPolicy(punctuation=PunctuationMode.REMOVE), ""),
        ("a / b", SearchNormalizationPolicy(punctuation=PunctuationMode.REMOVE), "a b"),
        ("ø ł", SearchNormalizationPolicy(strip_diacritics=True), "ø ł"),
        ("C++", SearchNormalizationPolicy(punctuation=PunctuationMode.REMOVE), "C++"),
    ],
)
def test_transformations_are_independent(value, policy, expected):
    assert normalize_search_input(value, policy=policy) == expected


@pytest.mark.parametrize(
    "casefold,diacritics,punctuation", list(product([False, True], [False, True], PunctuationMode))
)
def test_each_policy_is_idempotent(casefold, diacritics, punctuation):
    policy = SearchNormalizationPolicy(
        casefold=casefold, strip_diacritics=diacritics, punctuation=punctuation
    )
    for source in ["  Dónt\tStóp! ", "İ Straße / AC/DC", "東京 संगीत", "a\u0301—B"]:
        once = normalize_search_input(source, policy=policy)
        assert normalize_search_input(once, policy=policy) == once


@pytest.mark.parametrize("value", [None, 42, b"hello"])
def test_wrong_input_type_is_rejected(value):
    with pytest.raises(TypeError, match="value"):
        normalize_search_input(value)


@pytest.mark.parametrize(
    "kwargs", [{"casefold": 1}, {"strip_diacritics": "yes"}, {"punctuation": "remove"}]
)
def test_wrong_policy_values_are_rejected(kwargs):
    with pytest.raises(TypeError):
        SearchNormalizationPolicy(**kwargs)


def test_wrong_policy_type_is_rejected():
    with pytest.raises(TypeError, match="policy"):
        normalize_search_input("Hello", policy=None)
