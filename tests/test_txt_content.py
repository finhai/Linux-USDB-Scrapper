import codecs

import pytest

from usdb_scrapper.usdb_client import ContentDecodeError, decode_html, extract_txt


@pytest.mark.parametrize("encoding", ["utf-8", "cp1252", "iso-8859-1"])
def test_declared_encoding(encoding):
    text = "<textarea>#TITLE:Café für dich</textarea>"
    assert extract_txt(decode_html(text.encode(encoding), encoding)) == "#TITLE:Café für dich"


def test_undeclared_utf8_and_western_legacy():
    for encoding in ("utf-8", "cp1252"):
        text = "<textarea>“Café” €</textarea>"
        assert extract_txt(decode_html(text.encode(encoding))) == "“Café” €"


def test_bom_overrides_header():
    assert decode_html(codecs.BOM_UTF8 + "日本語".encode(), "cp1252") == "日本語"
    assert decode_html("Café".encode("utf-16")) == "Café"


def test_html_declaration():
    page = '<meta charset="windows-1252"><textarea>€</textarea>'
    assert extract_txt(decode_html(page.encode("cp1252"))) == "€"


@pytest.mark.parametrize("data,encoding", [(b"\xff", "utf-8"), (b"\x81", None), (b"x", "unknown")])
def test_invalid_encoding_fails_without_replacement(data, encoding):
    with pytest.raises(ContentDecodeError):
        decode_html(data, encoding)


def test_entities_once_and_literal_markup():
    page = (
        "<textarea>\n#TITLE:A &amp; B &#233; &amp;lt;\r\n: 0 1 2 <b>literal</b>\r\nE\n</textarea>"
    )
    assert extract_txt(page) == "#TITLE:A & B é &lt;\n: 0 1 2 <b>literal</b>\nE\n"


def test_ignores_fake_textarea_in_script_and_comment():
    page = '<script>"<textarea>fake</textarea>"</script><!-- <textarea>fake</textarea> -->'
    assert extract_txt(page + "<textarea>actual</textarea>") == "actual"


@pytest.mark.parametrize(
    "page",
    [
        "",
        "<textarea></textarea>",
        "<textarea>unfinished",
        "<textarea>a</textarea><textarea>b</textarea>",
    ],
)
def test_ambiguous_or_empty_payload_fails(page):
    with pytest.raises(ContentDecodeError):
        extract_txt(page)
