from collections.abc import Mapping

import pytest

from usdb_scrapper.usdb_client.txt import TxtClient, TxtRetrievalError

WAIT = """<form method="post" action="?link=gettxt&amp;id=3289">
<input type="hidden" name="wd" value="opaque&amp;value"></form>
<script>var time = 24; setTimeout(tick, 1000); document.forms[0].submit();</script>"""


class Session:
    def __init__(self, initial=WAIT, result="<textarea>#TITLE:Example</textarea>"):
        self.initial, self.result = initial, result
        self.events = []

    def get_html(self, path):
        self.events.append(("get", path))
        return self.initial

    def post_html(self, path: str, fields: Mapping[str, str]):
        self.events.append(("post", path, dict(fields)))
        return self.result


def test_wait_precedes_submission_and_preserves_field():
    session = Session()
    client = TxtClient(session, pause=lambda seconds: session.events.append(("wait", seconds)))
    assert client.retrieve_page(3289) == session.result
    assert session.events == [
        ("get", "/?link=gettxt&id=3289"),
        ("wait", 25),
        ("post", "/?link=gettxt&id=3289", {"wd": "opaque&value"}),
    ]


@pytest.mark.parametrize(
    "page",
    [
        WAIT.replace("?link=gettxt&amp;id=3289", "https://example.com/?link=gettxt&amp;id=3289"),
        WAIT.replace("id=3289", "id=9"),
        WAIT.replace('method="post"', 'method="get"'),
        WAIT.replace("time = 24", "time = 999"),
        WAIT.replace("1000", "500"),
        WAIT.replace("time = 24;", ""),
        WAIT.replace(".submit()", ".reset()"),
        WAIT.replace('value="opaque&amp;value"', 'value=""'),
        WAIT + WAIT,
        "<html>Unexpected page</html>",
    ],
)
def test_unknown_protocol_never_submits(page):
    session = Session(initial=page)
    with pytest.raises(TxtRetrievalError):
        TxtClient(session, pause=lambda _: pytest.fail("Must not wait")).retrieve_page(3289)
    assert len(session.events) == 1


@pytest.mark.parametrize("result", ["", "  ", WAIT])
def test_failed_followup_is_not_success(result):
    with pytest.raises(TxtRetrievalError):
        TxtClient(Session(result=result), pause=lambda _: None).retrieve_page(3289)


def test_cancel_during_wait_never_submits():
    session = Session()

    def cancel(_):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        TxtClient(session, pause=cancel).retrieve_page(3289)
    assert len(session.events) == 1


@pytest.mark.parametrize("song_id", [True, 0, -1, "3289"])
def test_invalid_id_never_requests(song_id):
    session = Session()
    with pytest.raises(ValueError):
        TxtClient(session).retrieve_page(song_id)
    assert session.events == []
