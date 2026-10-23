import pytest

from usdb_scrapper.usdb_client.details import (
    DetailClient,
    DetailParseError,
    parse_song_details,
    youtube_url,
)

VIDEO = "xFrGuyw1V8s"
CANONICAL = f"https://www.youtube.com/watch?v={VIDEO}"


def document(comment):
    return f"""<form action="?link=detail&id=3289&comment=1"></form>
    <a href="https://youtu.be/abcdefghijk">Outside</a>
    <table><tr class="list_head"><td>Comments by users (two cents)</td></tr>
    <tr class="list_tr1"><td>{comment}</td></tr>
    <tr class="list_tr2"><td>Write Comment</td></tr>
    <tr><td><textarea>https://youtu.be/abcdefghijk</textarea></td></tr></table>"""


@pytest.mark.parametrize(
    "comment",
    [
        f'<iframe src="https://www.youtube.com/embed/{VIDEO}"></iframe>',
        f'<a href="{CANONICAL}&amp;t=3">Video</a>',
        f"https://youtu.be/{VIDEO}",
        f"[youtube]{CANONICAL}[/youtube]",
        f'<iframe src="https://www.youtube-nocookie.com/embed/{VIDEO}"></iframe>',
    ],
)
def test_supported_comment_formats(comment):
    assert parse_song_details(document(comment), 3289).youtube_urls == (CANONICAL,)


def test_absence_is_explicit_and_script_and_editor_urls_ignored():
    html = document('<script>"https://youtu.be/abcdefghijk"</script>No video')
    assert parse_song_details(html, 3289).youtube_urls == ()


def test_duplicate_formats_collapse_and_multiple_videos_remain_available():
    html = document(f"{CANONICAL} https://youtu.be/{VIDEO} https://youtu.be/abcdefghijk")
    assert parse_song_details(html, 3289).youtube_urls == (
        CANONICAL,
        "https://www.youtube.com/watch?v=abcdefghijk",
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com.evil.example/watch?v=xFrGuyw1V8s",
        "https://youtube.com@evil.example/watch?v=xFrGuyw1V8s",
        "https://youtube.com/watch?v=short",
        "javascript:alert(1)",
        "https://www.youtube.com/channel/abcdefghijk",
        "https://www.youtube.com/watch?v=xFrGuyw1V8s&v=abcdefghijk",
    ],
)
def test_nonvideo_and_untrusted_urls_rejected(url):
    assert youtube_url(url) is None


def test_changed_or_wrong_page_is_not_reported_as_no_video():
    for html in ("<p>error</p>", document("none").replace("id=3289", "id=9")):
        with pytest.raises(DetailParseError):
            parse_song_details(html, 3289)


def test_client_uses_exact_song_id():
    class Session:
        def get_html(self, path):
            assert path == "/?link=detail&id=3289"
            return document(CANONICAL)

    assert DetailClient(Session()).fetch(3289).youtube_urls == (CANONICAL,)
    with pytest.raises(ValueError):
        DetailClient(Session()).fetch(True)
