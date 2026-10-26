"""Conservative search normalization independent of filesystem naming."""

import unicodedata


def normalize_search_input(value: str) -> str:
    """Normalize spacing and ASCII case; preserve meaningful punctuation/accents.

    Live USDB tests matched ASCII case variants but not doubled/outer spaces or
    accent substitutions. General transliteration and punctuation removal would
    change queries without evidence, so they are intentionally not performed.
    """
    if not isinstance(value, str):
        raise TypeError("Search input must be text")
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    return normalized.translate(
        str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
    )
