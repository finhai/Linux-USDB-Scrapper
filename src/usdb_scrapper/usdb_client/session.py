"""Synchronous authenticated USDB session; call from a worker, not the GUI thread."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from html.parser import HTMLParser
from types import TracebackType
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx

from usdb_scrapper.credential_manager import CredentialProvider
from usdb_scrapper.usdb_client.content import decode_html
from usdb_scrapper.usdb_client.session_errors import UsdbError as UsdbError

ORIGIN = "https://usdb.animux.de"
LOGIN_URL = ORIGIN + "/?link=login"
LIST_URL = ORIGIN + "/?link=list"


class AuthenticationError(UsdbError):
    """Authentication was required or could not be confirmed."""


class SessionExpiredError(AuthenticationError):
    """A previously authenticated request requires login again."""


class TransportError(UsdbError):
    """Network, HTTP, or redirect failure."""


class LoginFormError(UsdbError):
    """The current login form does not match the supported protocol."""


@dataclass
class _Form:
    action: str
    method: str
    inputs: list[dict[str, str | None]] = field(default_factory=list)


class _Page(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__()
        self.forms: list[_Form] = []
        self.current: _Form | None = None
        self.links: list[str] = []
        self.text: list[str] = []
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "form":
            self.current = _Form(
                values.get("action") or "", (values.get("method") or "get").lower()
            )
            self.forms.append(self.current)
        elif tag == "input" and self.current is not None:
            self.current.inputs.append(values)
        elif tag == "a":
            self.links.append(values.get("href") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.current = None

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    @property
    def denied(self) -> bool:
        return "you are not logged in" in " ".join(" ".join(self.text).lower().split())

    @property
    def has_login_form(self) -> bool:
        return any(
            {"user", "pass"}.issubset({item.get("name") for item in form.inputs})
            and any(
                item.get("name") == "pass" and (item.get("type") or "").lower() == "password"
                for item in form.inputs
            )
            for form in self.forms
        )

    @property
    def has_logout(self) -> bool:
        return any(
            _same_origin(urljoin(ORIGIN, href))
            and parse_qs(urlsplit(href).query).get("link") == ["logout"]
            for href in self.links
        )


def _same_origin(url: str) -> bool:
    try:
        parts = urlsplit(url)
        return parts.scheme == "https" and parts.netloc == "usdb.animux.de"
    except ValueError:
        return False


class UsdbSession:
    """One in-memory session. Single-worker ownership; one optional retry after session expiry.

    Close explicitly or use a context manager. Closing clears local cookies,
    not the session on the remote server. Never log returned HTML or credentials.
    """

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        credential_provider: CredentialProvider | None = None,
    ) -> None:
        self._client = httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(20, connect=10),
            follow_redirects=False,
            headers={"User-Agent": "USDB-Scrapper/0.1"},
        )
        self._authenticated = False
        self._credential_provider = credential_provider

    @property
    def authenticated(self) -> bool:
        """Last verified state, not a guarantee that the server has not expired it."""
        return self._authenticated and not self._client.is_closed

    def __enter__(self) -> "UsdbSession":
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._forget_session()
        self._client.close()

    def _ensure_open(self) -> None:
        if self._client.is_closed:
            raise UsdbError("Session is closed")

    def _forget_session(self) -> None:
        self._authenticated = False
        self._client.cookies.clear()

    def login(self, username: str, password: str) -> None:
        """Submit credentials once and verify protected-page access afterward."""
        self._ensure_open()
        self._forget_session()
        if not isinstance(username, str) or not isinstance(password, str):
            raise TypeError("Username and password must be strings")
        if not username.strip() or not password:
            raise ValueError("Username and password must not be empty")
        fields: dict[str, str] = {}
        try:
            response = self._request("GET", LOGIN_URL)
            page = _Page(decode_html(response.content, response.charset_encoding))
            forms = [
                form
                for form in page.forms
                if any((item.get("type") or "").lower() == "password" for item in form.inputs)
            ]
            if len(forms) != 1 or forms[0].method != "post":
                raise LoginFormError("Expected one POST login form")
            form = forms[0]
            names = {item.get("name") for item in form.inputs}
            if not {"user", "pass"}.issubset(names):
                raise LoginFormError("Login fields have changed")
            action = urljoin(str(response.url), form.action)
            if not _same_origin(action):
                raise LoginFormError("Login destination is not the trusted origin")
            for item in form.inputs:
                name = item.get("name")
                if (
                    name
                    and "disabled" not in item
                    and (item.get("type") or "").lower() in ("hidden", "submit")
                ):
                    fields[name] = item.get("value") or ""
            fields.pop("remember", None)
            fields.update(user=username, **{"pass": password})
            self._request("POST", action, fields)
            page = _Page(self._request("GET", LIST_URL).text)
            if (
                page.denied
                or page.has_login_form
                or not page.has_logout
                or not any(cookie.name == "PHPSESSID" for cookie in self._client.cookies.jar)
            ):
                raise AuthenticationError("USDB login could not be confirmed")
            self._authenticated = True
        except UsdbError:
            self._forget_session()
            raise
        finally:
            fields.clear()

    def get_html(self, path: str = "/?link=list") -> str:
        """Read a same-origin page using this authenticated session."""
        return self._with_reauthentication("GET", path)

    def post_html(self, path: str, fields: Mapping[str, str]) -> str:
        """Submit same-origin form data using this session (e.g. a search)."""
        return self._with_reauthentication("POST", path, dict(fields))

    def _with_reauthentication(
        self, method: str, path: str, fields: dict[str, str] | None = None
    ) -> str:
        try:
            return self._authenticated_html(method, path, fields)
        except SessionExpiredError:
            if self._credential_provider is None:
                raise
            credentials = self._credential_provider.get_credentials()
            if credentials is None:
                raise
            try:
                self.login(credentials.username, credentials.password)
            finally:
                del credentials
        # Deliberately outside the handler: a second expiry is not retried.
        return self._authenticated_html(method, path, fields)

    def _authenticated_html(
        self, method: str, path: str, fields: dict[str, str] | None = None
    ) -> str:
        self._ensure_open()
        if not self.authenticated:
            raise AuthenticationError("Login is required")
        try:
            response = self._request(
                method, urljoin(ORIGIN + "/", path), fields, authenticated_request=True
            )
            page = _Page(decode_html(response.content, response.charset_encoding))
            if page.denied or page.has_login_form:
                raise SessionExpiredError("USDB requires login again")
        except AuthenticationError:
            self._forget_session()
            raise SessionExpiredError("USDB requires login again") from None
        return decode_html(response.content, response.charset_encoding)

    def _request(
        self,
        method: str,
        url: str,
        fields: dict[str, str] | None = None,
        *,
        authenticated_request: bool = False,
    ) -> httpx.Response:
        for _ in range(6):
            if not _same_origin(url):
                raise TransportError("Request destination is not the trusted origin")
            if authenticated_request and "login" in parse_qs(urlsplit(url).query).get("link", []):
                raise SessionExpiredError("USDB requires login again")
            try:
                response = self._client.request(method, url, data=fields)
            except httpx.HTTPError:
                # Transport exceptions can retain requests; do not expose them to UI/loggers.
                raise TransportError("USDB request failed") from None
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    raise TransportError("Redirect did not include a destination")
                url = urljoin(str(response.url), location)
                if response.status_code == 303 or (
                    response.status_code in (301, 302) and method == "POST"
                ):
                    method, fields = "GET", None
                continue
            if response.status_code in (401, 403):
                raise AuthenticationError("USDB refused access")
            if not 200 <= response.status_code < 300:
                raise TransportError(f"USDB returned HTTP {response.status_code}")
            return response
        raise TransportError("USDB redirected too many times")
