"""Protocol tests with synthetic responses; never contact USDB."""

from urllib.parse import parse_qs

import httpx
import pytest

from usdb_scrapper.usdb_client import (
    AuthenticationError,
    LoginFormError,
    SessionExpiredError,
    TransportError,
    UsdbError,
    UsdbSession,
)

FORM = """<form method="post" action="?link=login">
<input name="user"><input name="pass" type="password">
<input name="nonce" type="hidden" value="synthetic">
<input name="remember" type="checkbox" value="1">
<input name="login" type="submit" value="Login"></form>"""
PROTECTED = '<a href="?link=logout">Logout</a><p>Protected content</p>'


class Server:
    def __init__(self):
        self.requests = []
        self.fail_login = False
        self.expired = False
        self.form = FORM
        self.bad_destination = None

    def __call__(self, request):
        self.requests.append(request)
        link = request.url.params.get("link")
        if link == "login" and request.method == "GET":
            return httpx.Response(
                200, text=self.form, headers={"set-cookie": "PHPSESSID=pre; Path=/; Secure"}
            )
        if link == "login":
            assert "PHPSESSID=pre" in request.headers.get("cookie", "")
            assert parse_qs(request.content.decode()) == {
                "user": ["demo"],
                "pass": ["synthetic-secret"],
                "nonce": ["synthetic"],
                "login": ["Login"],
            }
            return httpx.Response(
                302,
                headers={
                    "location": self.bad_destination or "/?link=list",
                    "set-cookie": "PHPSESSID=authenticated; Path=/; Secure",
                },
            )
        if self.fail_login or self.expired:
            return httpx.Response(200, text="You are not logged in. Login to use this function.")
        if "PHPSESSID=authenticated" not in request.headers.get("cookie", ""):
            return httpx.Response(200, text=FORM)
        return httpx.Response(200, text=PROTECTED)


@pytest.fixture
def setup():
    server = Server()
    with UsdbSession(transport=httpx.MockTransport(server)) as session:
        yield session, server


def login(session):
    session.login("demo", "synthetic-secret")


def test_login_and_later_get_post_reuse_cookie(setup):
    session, server = setup
    login(session)
    assert session.authenticated
    assert "Protected content" in session.get_html()
    assert "Protected content" in session.post_html("/?link=list", {"title": "Don't Stop"})
    assert parse_qs(server.requests[-1].content.decode()) == {"title": ["Don't Stop"]}
    assert server.requests[2].method == "GET"  # POST/302 changes to GET.


def test_access_before_login_does_not_send_request(setup):
    session, server = setup
    with pytest.raises(AuthenticationError):
        session.get_html()
    assert server.requests == []


def test_failed_login_clears_state_and_cookies(setup):
    session, server = setup
    login(session)
    server.fail_login = True
    with pytest.raises(AuthenticationError):
        login(session)
    assert not session.authenticated
    assert not list(session._client.cookies.jar)


def test_expired_session_is_not_returned_as_success(setup):
    session, server = setup
    login(session)
    server.expired = True
    with pytest.raises(AuthenticationError):
        session.get_html()
    assert not session.authenticated
    assert not list(session._client.cookies.jar)


@pytest.mark.parametrize(
    "destination",
    [
        "https://evil.example/",
        "http://usdb.animux.de/",
        "https://user@usdb.animux.de/",
        "https://usdb.animux.de:8443/",
    ],
)
def test_external_redirect_never_receives_request(setup, destination):
    session, server = setup
    server.bad_destination = destination
    with pytest.raises(TransportError):
        login(session)
    assert len(server.requests) == 2
    assert not session.authenticated


def test_bad_form_action_rejected_before_credential_post(setup):
    session, server = setup
    server.form = FORM.replace("?link=login", "https://evil.example/")
    with pytest.raises(LoginFormError):
        login(session)
    assert len(server.requests) == 1


@pytest.mark.parametrize(
    "form",
    [
        "<p>unexpected</p>",
        FORM + FORM,
        FORM.replace('method="post"', 'method="get"'),
        FORM.replace('name="user"', 'name="changed"'),
    ],
)
def test_form_changes_fail_closed(setup, form):
    session, server = setup
    server.form = form
    with pytest.raises(LoginFormError):
        login(session)
    assert len(server.requests) == 1


@pytest.mark.parametrize(
    "status,error",
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (429, TransportError),
        (500, TransportError),
    ],
)
def test_http_errors_are_typed(status, error):
    with UsdbSession(
        transport=httpx.MockTransport(lambda request: httpx.Response(status))
    ) as session:
        with pytest.raises(error):
            login(session)
        assert not session.authenticated


def test_network_error_has_sanitized_message():
    def fail(request):
        raise httpx.ConnectError("synthetic-secret", request=request)

    with UsdbSession(transport=httpx.MockTransport(fail)) as session:
        with pytest.raises(TransportError) as caught:
            login(session)
        assert "synthetic-secret" not in str(caught.value)
        assert caught.value.__suppress_context__


def test_redirect_loop_is_bounded():
    calls = []

    def loop(request):
        calls.append(request)
        return httpx.Response(302, headers={"location": "/?link=login"})

    with UsdbSession(transport=httpx.MockTransport(loop)) as session:
        with pytest.raises(TransportError, match="too many"):
            login(session)
    assert len(calls) == 6


def test_close_clears_local_session(setup):
    session, _ = setup
    login(session)
    session.close()
    assert not session.authenticated
    assert not list(session._client.cookies.jar)
    with pytest.raises(UsdbError, match="closed"):
        session.get_html()
    session.close()


@pytest.mark.parametrize("username,password", [("", "x"), (" ", "x"), ("x", "")])
def test_blank_credentials_do_not_send_requests(setup, username, password):
    session, server = setup
    with pytest.raises(ValueError):
        session.login(username, password)
    assert not server.requests


def test_external_request_after_login_is_rejected(setup):
    session, server = setup
    login(session)
    count = len(server.requests)
    with pytest.raises(TransportError):
        session.get_html("https://evil.example/")
    assert len(server.requests) == count


@pytest.mark.parametrize(
    "verification",
    [
        "<p>HTTP 200 without proof</p>",
        FORM,
        '<a href="https://evil.example/?link=logout">Logout</a>',
    ],
)
def test_login_requires_positive_same_origin_evidence(verification):
    def handler(request):
        if request.url.params.get("link") == "login":
            return httpx.Response(200, text=FORM, headers={"set-cookie": "PHPSESSID=pre; Path=/"})
        return httpx.Response(200, text=verification)

    with UsdbSession(transport=httpx.MockTransport(handler)) as session:
        with pytest.raises(AuthenticationError):
            login(session)


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text=FORM),
        httpx.Response(200, text="You are <b>not</b> logged\n in. Login to use this function."),
        httpx.Response(401),
        httpx.Response(403),
        *[
            httpx.Response(status, headers={"location": "/?link=login"})
            for status in (301, 302, 303, 307, 308)
        ],
    ],
)
def test_expiry_signals_clear_session_without_retry(method, response):
    server = Server()
    expired = False
    calls = []

    def handler(request):
        calls.append(request)
        return response if expired else server(request)

    with UsdbSession(transport=httpx.MockTransport(handler)) as session:
        login(session)
        expired = True
        before = len(calls)
        with pytest.raises(SessionExpiredError):
            if method == "GET":
                session.get_html()
            else:
                session.post_html("/?link=list", {"title": "sample"})
        assert len(calls) == before + 1
        assert not session.authenticated
        assert not list(session._client.cookies.jar)
        with pytest.raises(AuthenticationError):
            session.get_html()
        assert len(calls) == before + 1
        expired = False
        login(session)
        assert session.get_html() == PROTECTED


@pytest.mark.parametrize("status", [429, 500, 503])
def test_server_errors_do_not_claim_session_expired(status):
    server = Server()
    failing = False

    def handler(request):
        return httpx.Response(status) if failing else server(request)

    with UsdbSession(transport=httpx.MockTransport(handler)) as session:
        login(session)
        failing = True
        with pytest.raises(TransportError):
            session.get_html()
        assert session.authenticated


def test_missing_logout_or_unrelated_password_form_does_not_imply_expiry():
    server = Server()
    content = None

    def handler(request):
        return httpx.Response(200, text=content) if content is not None else server(request)

    with UsdbSession(transport=httpx.MockTransport(handler)) as session:
        login(session)
        content = '<form><input type="password" name="new_password"></form>'
        assert session.get_html() == content
        assert session.authenticated


def test_deliberately_invalid_cookie_is_detected(setup):
    session, server = setup
    login(session)
    session._client.cookies.clear()
    session._client.cookies.set("PHPSESSID", "invalid", domain="usdb.animux.de", path="/")
    with pytest.raises(SessionExpiredError):
        session.get_html()
    assert "PHPSESSID=invalid" in server.requests[-1].headers["cookie"]
    assert not session.authenticated


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_expiry_reauthenticates_and_retries_original_operation_once(method):
    from usdb_scrapper.credential_manager import Credentials

    server = Server()
    expired_once = False
    operations = []

    class Provider:
        calls = 0

        def get_credentials(self):
            self.calls += 1
            return Credentials("demo", "synthetic-secret")

    def handler(request):
        nonlocal expired_once
        if request.url.params.get("link") == "search":
            operations.append((request.method, request.content))
            if not expired_once:
                expired_once = True
                return httpx.Response(200, text=FORM)
        return server(request)

    provider = Provider()
    with UsdbSession(
        transport=httpx.MockTransport(handler), credential_provider=provider
    ) as session:
        login(session)
        result = (
            session.get_html("/?link=search")
            if method == "GET"
            else session.post_html("/?link=search", {"title": "Don't Stop"})
        )
        assert result == PROTECTED
        assert session.authenticated
        assert provider.calls == 1
        assert len(operations) == 2
        assert operations[0] == operations[1]


@pytest.mark.parametrize("mode", ["missing", "bad_login", "second_expiry", "network", "initial"])
def test_reauthentication_is_bounded_and_only_for_expiry(mode):
    from usdb_scrapper.credential_manager import Credentials

    server = Server()
    operations = []

    class Provider:
        calls = 0

        def get_credentials(self):
            self.calls += 1
            if mode == "missing":
                return None
            if mode == "bad_login":
                server.fail_login = True
            return Credentials("demo", "synthetic-secret")

    def handler(request):
        if request.url.params.get("link") == "search":
            operations.append(request)
            return httpx.Response(500 if mode == "network" else 401)
        return server(request)

    provider = Provider()
    with UsdbSession(
        transport=httpx.MockTransport(handler), credential_provider=provider
    ) as session:
        if mode != "initial":
            login(session)
        with pytest.raises(TransportError if mode == "network" else AuthenticationError):
            session.get_html("/?link=search")
        assert provider.calls == (0 if mode in ("initial", "network") else 1)
        assert len(operations) == (0 if mode == "initial" else 2 if mode == "second_expiry" else 1)


def test_credentials_repr_hides_secrets():
    from usdb_scrapper.credential_manager import Credentials

    assert repr(Credentials("private-user", "private-password")) == "Credentials()"
