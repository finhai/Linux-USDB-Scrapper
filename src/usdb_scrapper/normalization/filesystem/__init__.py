"""Deterministic portable name components, independent of search normalization."""

import hashlib
import unicodedata

MAX_COMPONENT_LENGTH = 58


def normalize_filesystem_name(value: str) -> str:
    """Return one lowercase ASCII-alphanumeric directory name or file stem.

    NFC-equivalent strings share a name. Other distinctions (including case and
    punctuation) enter the digest even when lost from the readable prefix.
    No filesystem access, extension handling, or artist identity inference occurs.
    """
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    if not value.strip():
        raise ValueError("value must not be blank")
    canonical = unicodedata.normalize("NFC", value)
    try:
        encoded = canonical.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("value must contain valid Unicode scalar values") from exc
    readable = (
        "".join(
            char
            for char in unicodedata.normalize("NFKD", canonical).casefold()
            if "a" <= char <= "z" or "0" <= char <= "9"
        )[:24]
        or "item"
    )
    digest = hashlib.sha256(encoded).hexdigest()[:32]
    # Prefix avoids device names and the fixed-length digest disambiguates slugs.
    return f"n{readable}x{digest}"


__all__ = ["MAX_COMPONENT_LENGTH", "normalize_filesystem_name"]


def readable_filesystem_name(value: str) -> str:
    """Preserve readable Unicode names; suffix only lossy sanitization/truncation."""
    import re

    if not isinstance(value, str) or not value.strip():
        raise ValueError("Name must not be blank")
    original = unicodedata.normalize("NFC", value).strip()
    original.encode("utf-8")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "-", original).rstrip(" .")
    if not name or name in (".", ".."):
        name = "Untitled"
    if name.split(".")[0].upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
        "COM¹",
        "COM²",
        "COM³",
        "LPT¹",
        "LPT²",
        "LPT³",
    }:
        name = "_" + name
    while len(name.encode("utf-8")) > 90:
        name = name[:-1]
    name = name.rstrip(" .")
    if name != original:
        name += " [" + hashlib.sha256(original.encode()).hexdigest()[:8] + "]"
    return name
