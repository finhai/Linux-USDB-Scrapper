# USDB authenticated session — card 15

The login spike confirmed an ordinary form POST over HTTPS with a cookie jar.
UsdbSession implements that mechanism using HTTPX. It fetches the current form,
submits credentials once, then verifies the protected list has a logout link, no
login prompt, and a PHPSESSID cookie. A cookie alone is not proof of login.

```python
from usdb_scrapper.usdb_client import UsdbSession

with UsdbSession() as session:
    session.login(username, password)
    html = session.get_html("/?link=list")
```

Own this synchronous client in a single worker, never the GUI thread. get_html
and post_html reuse cookies and return HTML for future parsers. Requests and
redirects are restricted to https://usdb.animux.de, with finite timeouts and a
redirect limit. There are no automatic retries or persistent credentials/cookies.
Closing clears local cookies and connections, not the remote server session.

AuthenticationError, LoginFormError and TransportError inherit UsdbError and use
sanitized messages. Never log credentials, cookies or response HTML. Failed login
and explicit expiry clear authentication. The authenticated property records the
last verified state; it cannot predict server expiry. GUI integration, secure
credential storage, reauthentication and parsers remain separate cards.

## Validation

27 offline tests cover cookie reuse, protected-page verification, failed re-login,
expiry, redirects, untrusted destinations, changed forms, errors and cleanup.
Production-client live acceptance passed on 2026-10-19. The maintainer ran the
client check against USDB and reported login_verified=true and
subsequent_request_succeeded=true. No credentials or cookies were recorded. Run this command in your terminal:

```sh
cd /home/faule/MySoftware/Linux-USDB-Scrapper && .venv/bin/python scripts/check_usdb_session.py
```

Enter credentials only at hidden prompts. Share only the JSON summary. Both
login_verified and subsequent_request_succeeded must be true.

## Session expiry — card 16

Authenticated requests raise SessionExpiredError (an AuthenticationError subtype)
on HTTP 401/403, a redirect to the login endpoint, the USDB user/pass login form,
or the site's login-required message. Login redirects are stopped before another
request is sent, including 307/308 redirects that would otherwise replay POST data.
Cookies and the authenticated flag are cleared, and subsequent requests fail
locally until login succeeds again. Initial login failure remains AuthenticationError.

HTTP 429/5xx and network failures remain TransportError and do not claim expiry.
A missing logout link alone is not enough: authenticated fragments may omit it.
Detection covers these known signals; an unrelated or redesigned HTML page needs
validation by its future content parser. HTTP 403 is conservatively treated as
requiring login; it does not prove the server's underlying reason for denying access.

Offline acceptance uses a deliberately invalid cookie and checks both GET and
POST expiry paths, cleanup, no retry, and successful explicit re-login. This does
not claim a new live-site expiry experiment. Automatic reauthentication is card 17.

This feature branch depends on the session-client PR #8. Merge that PR first;
retarget this feature PR to dev afterward.
