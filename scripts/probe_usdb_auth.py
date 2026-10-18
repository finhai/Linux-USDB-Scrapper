"""Manual card-14 investigation. Credentials/cookies live in memory only.

Run with --inspect for public form details or --login in your own terminal for
one credential POST followed by a protected-page request. Not production code.
"""

import argparse
import getpass
import http.cookiejar
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

ORIGIN = "https://usdb.animux.de"
LOGIN_URL = ORIGIN + "/?link=login"
LIST_URL = ORIGIN + "/?link=list"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None
        self.links = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.current = {
                "method": attrs.get("method", "get").lower(),
                "action": attrs.get("action", ""),
                "inputs": [],
            }
            self.forms.append(self.current)
        elif tag == "input" and self.current is not None:
            self.current["inputs"].append(attrs)
        elif tag == "a":
            self.links.append(attrs.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None

    def handle_data(self, data):
        self.text.append(data)


def same_origin(url):
    parsed = urllib.parse.urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "usdb.animux.de"
        and parsed.username is None
        and parsed.password is None
    )


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not same_origin(newurl):
            raise ValueError("Unexpected redirect; request stopped")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def request(opener, url, fields=None):
    if not same_origin(url):
        raise ValueError("Unexpected destination; request stopped")
    data = None if fields is None else urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "USDB-Scrapper-auth-spike"})
    with opener.open(req, timeout=20) as response:
        page = Page()
        page.feed(response.read().decode("utf-8", errors="replace"))
        return page


def login_form(page):
    matches = [
        form
        for form in page.forms
        if any(item.get("type", "").lower() == "password" for item in form["inputs"])
    ]
    if len(matches) != 1 or matches[0]["method"] != "post":
        raise ValueError("Expected one POST login form")
    form = matches[0]
    names = {item.get("name") for item in form["inputs"]}
    if not {"user", "pass"}.issubset(names):
        raise ValueError("Login form changed; inspect it before submitting credentials")
    action = urllib.parse.urljoin(LOGIN_URL, form["action"])
    if not same_origin(action):
        raise ValueError("Login form destination changed")
    return form, action


def login_required(page):
    return "not logged in" in " ".join(page.text).lower()


def has_logout_link(page):
    return any(
        same_origin(urllib.parse.urljoin(ORIGIN, href))
        and urllib.parse.parse_qs(urllib.parse.urlsplit(href).query).get("link") == ["logout"]
        for href in page.links
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--login", action="store_true")
    args = parser.parse_args()
    if args.login and not sys.stdin.isatty():
        print("Run --login in your own interactive terminal; do not pipe credentials.")
        return 2
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), SafeRedirect())
    try:
        page = request(opener, LOGIN_URL)
        form, action = login_form(page)
        report = {
            "method": form["method"],
            "input_names": [item["name"] for item in form["inputs"] if "name" in item],
            "session_cookie_before_login": any(cookie.name == "PHPSESSID" for cookie in jar),
        }
        if args.inspect:
            print(json.dumps(report, indent=2))
            return 0
        baseline = request(opener, LIST_URL)
        if not login_required(baseline):
            print("Inconclusive: public baseline changed; no credentials submitted.")
            return 2
        # Refresh the form in case the baseline request affects server-side state.
        form, action = login_form(request(opener, LOGIN_URL))
        fields = {
            item["name"]: item.get("value", "")
            for item in form["inputs"]
            if item.get("type", "").lower() in ("hidden", "submit") and "name" in item
        }
        fields.pop("remember", None)
        fields["user"] = getpass.getpass("USDB username (hidden): ")
        fields["pass"] = getpass.getpass("USDB password (hidden): ")
        if not fields["user"] or not fields["pass"]:
            fields.clear()
            print("Cancelled: blank credentials; no login submitted.")
            return 2
        request(opener, action, fields)
        fields.clear()
        protected = request(opener, LIST_URL)
        report.update(
            {
                "baseline_required_login": True,
                "protected_page_requires_login": login_required(protected),
                "protected_page_has_logout_link": has_logout_link(protected),
                "session_cookie_after_login": any(cookie.name == "PHPSESSID" for cookie in jar),
            }
        )
        report["plain_http_login_confirmed"] = (
            not report["protected_page_requires_login"]
            and report["protected_page_has_logout_link"]
            and report["session_cookie_after_login"]
        )
        print(json.dumps(report, indent=2))
        return 0 if report["plain_http_login_confirmed"] else 2
    except (urllib.error.URLError, ValueError, OSError):
        # Never print exception text, page contents, cookies, or a request body.
        print(
            "Probe inconclusive: network, form, or redirect validation failed. No details logged."
        )
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Probe cancelled.")
        return 2
    finally:
        jar.clear()


if __name__ == "__main__":
    raise SystemExit(main())
