"""Pure search-input normalization; independent of filesystem naming."""

import unicodedata
from dataclasses import dataclass
from enum import Enum


class PunctuationMode(Enum):
    PRESERVE = "preserve"
    REMOVE = "remove"
    SPACE = "space"


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchNormalizationPolicy:
    """Opt into lossy transformations only after validating server behavior."""

    casefold: bool = False
    strip_diacritics: bool = False
    punctuation: PunctuationMode = PunctuationMode.PRESERVE

    def __post_init__(self) -> None:
        if type(self.casefold) is not bool:
            raise TypeError("casefold must be a bool")
        if type(self.strip_diacritics) is not bool:
            raise TypeError("strip_diacritics must be a bool")
        if not isinstance(self.punctuation, PunctuationMode):
            raise TypeError("punctuation must be a PunctuationMode")


_DEFAULT_POLICY = SearchNormalizationPolicy()


def normalize_search_input(
    value: str, *, policy: SearchNormalizationPolicy = _DEFAULT_POLICY
) -> str:
    """Normalize Unicode/whitespace and apply explicitly selected transforms.

    Empty input stays empty; the caller decides whether an empty query is valid.
    Original metadata is never modified. No requests or filename handling occur.
    """
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    if not isinstance(policy, SearchNormalizationPolicy):
        raise TypeError("policy must be a SearchNormalizationPolicy")
    result = unicodedata.normalize("NFC", value)
    if policy.casefold:
        result = result.casefold()
    if policy.strip_diacritics:
        result = "".join(
            char
            for char in unicodedata.normalize("NFD", result)
            if not unicodedata.category(char).startswith("M")
        )
    if policy.punctuation is not PunctuationMode.PRESERVE:
        replacement = " " if policy.punctuation is PunctuationMode.SPACE else ""
        result = "".join(
            replacement if unicodedata.category(char).startswith("P") else char for char in result
        )
    return " ".join(unicodedata.normalize("NFC", result).split())


__all__ = ["PunctuationMode", "SearchNormalizationPolicy", "normalize_search_input"]
