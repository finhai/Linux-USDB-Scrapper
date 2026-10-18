"""Safety/interpretation tests for the manual spike; no network or credentials."""

import importlib.util
from pathlib import Path
from urllib.request import Request

import pytest

_spec = importlib.util.spec_from_file_location(
    "auth_probe", Path(__file__).parents[1] / "scripts" / "probe_usdb_auth.py"
)
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


def page(html):
    result = probe.Page()
    result.feed(html)
    return result


def test_selects_password_form_and_preserves_hidden_fields():
    document = page("""
    <form action="?link=list"><input name="title"></form>
    <form method="POST" action="">
      <input name="user"><input name="pass" type="password">
      <input name="nonce" type="hidden" value="synthetic-test-token">
      <input name="login" type="submit" value="Login">
    </form>
    """)
    form, action = probe.login_form(document)
    assert action == probe.LOGIN_URL
    assert [item.get("name") for item in form["inputs"]] == ["user", "pass", "nonce", "login"]


@pytest.mark.parametrize(
    "action", ["http://usdb.animux.de/", "https://evil.example/", "//evil.example/"]
)
def test_form_cannot_redirect_credentials(action):
    document = page(f'''<form method="post" action="{action}">
    <input name="user"><input name="pass" type="password"></form>''')
    with pytest.raises(ValueError):
        probe.login_form(document)


@pytest.mark.parametrize(
    "url",
    [
        "http://usdb.animux.de/",
        "https://evil.example/",
        "https://usdb.animux.de.evil.example/",
        "https://user@usdb.animux.de/",
        "https://usdb.animux.de:8443/",
    ],
)
def test_unsafe_redirects_rejected(url):
    handler = probe.SafeRedirect()
    with pytest.raises(ValueError):
        handler.redirect_request(Request(probe.LOGIN_URL), None, 302, "Found", {}, url)


def test_same_origin_redirect_is_allowed():
    result = probe.SafeRedirect().redirect_request(
        Request(probe.LOGIN_URL), None, 302, "Found", {}, probe.LIST_URL
    )
    assert result.full_url == probe.LIST_URL


def test_login_notice_detected_across_tags():
    assert probe.login_required(page("You are <b>not logged in</b>. Login to use this function."))


def test_positive_marker_must_be_same_origin_logout_link():
    assert probe.has_logout_link(page('<a href="?link=logout">Logout</a>'))
    assert not probe.has_logout_link(page('<a href="https://evil.example/?link=logout">Logout</a>'))
    assert not probe.has_logout_link(page("<p>Logout</p>"))
    assert not probe.has_logout_link(page('<a href="?link=login">Login</a>'))


@pytest.mark.parametrize(
    "html",
    [
        "",
        '<form method="get"><input type="password"></form>',
        '<form method="post"><input name="changed" type="password"></form>',
    ],
)
def test_unrecognized_form_fails_closed(html):
    with pytest.raises(ValueError):
        probe.login_form(page(html))
