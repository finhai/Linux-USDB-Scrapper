"""Decode response bytes and extract textarea text without interpreting song tags."""

import codecs
import re
from html import unescape
from html.parser import HTMLParser

from usdb_scrapper.usdb_client.session_errors import ContentDecodeError


def decode_html(content: bytes, charset: str | None = None) -> str:
    """BOM, explicit charset, HTML declaration, then UTF-8/Windows-1252.

    No replacement characters are introduced. Undeclared legacy bytes use the
    Western HTML fallback; unknown encodings cannot be inferred universally.
    """
    if content.startswith(codecs.BOM_UTF8):
        encoding = "utf-8-sig"
    elif content.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        encoding = "utf-16"
    else:
        if not charset:
            match = re.search(
                rb"<meta\b[^>]*\bcharset\s*=\s*[\"']?\s*([a-zA-Z0-9_-]+)",
                content[:4096],
                re.IGNORECASE,
            )
            charset = match[1].decode("ascii") if match else None
        if charset:
            encoding = charset.strip().lower()
            if encoding in ("iso-8859-1", "latin1", "latin-1", "us-ascii"):
                encoding = "cp1252"
        else:
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                encoding = "cp1252"
    try:
        return content.decode(encoding, errors="strict")
    except (LookupError, UnicodeError):
        raise ContentDecodeError("USDB response encoding is unsupported or invalid") from None


class _Textarea(HTMLParser):
    def __init__(self, page: str):
        super().__init__(convert_charrefs=False)
        self.blocks: list[list[str]] = []
        self.current: list[str] | None = None
        self.feed(page)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "textarea":
            self.set_cdata_mode("textarea")
            self.current = []
            self.blocks.append(self.current)

    def handle_endtag(self, tag: str) -> None:
        if tag == "textarea":
            self.current = None

    def handle_entityref(self, name: str) -> None:
        self.handle_data("&" + name + ";")

    def handle_charref(self, name: str) -> None:
        self.handle_data("&#" + name + ";")

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current.append(data)


def extract_txt(page: str) -> str:
    """Return one textarea's browser-visible text, decoding entities exactly once."""
    parsed = _Textarea(page)
    if len(parsed.blocks) != 1 or parsed.current is not None:
        raise ContentDecodeError("Expected one complete TXT textarea")
    result = unescape("".join(parsed.blocks[0])).replace("\r\n", "\n").replace("\r", "\n")
    # HTML textarea rendering removes one initial newline.
    if result.startswith("\n"):
        result = result[1:]
    if not result.strip():
        raise ContentDecodeError("TXT textarea is empty")
    return result
