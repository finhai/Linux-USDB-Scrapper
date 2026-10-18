# USDB authentication spike — card 14

Investigation date: 2026-10-18. This is a research tool, not the production client.

## Public observations verified

A GET of https://usdb.animux.de/?link=login returns one password form with method
POST and an empty action (submit to the same login URL). Its inputs are `user`
(text), `pass` (password), `remember` (checkbox, value 1), and `login` (submit,
value Login). No hidden token was present inside the inspected login form.
The response issues PHPSESSID before credentials are submitted. Merely obtaining
that cookie therefore proves neither authentication nor successful login.

Unauthenticated requests to ?link=list return HTTP 200 and a search page title,
but their body says login is required. Status codes/titles alone cannot establish
success. No password attempt was made during public inspection.

## Manual verification

From the repository root, run:

```sh
.venv/bin/python scripts/probe_usdb_auth.py --login
```

On Windows use `.venv\Scripts\python.exe` instead. The --inspect mode needs no
credentials and prints the form field names and presence of a session cookie.

The login mode uses hidden terminal prompts, performs one credential POST over
HTTPS, then requests the protected listing with the same in-memory cookie jar.
It disables remember-me by omitting its checkbox field, does not write captures
or cookies, and prints only form names and boolean evidence. It blocks redirects
and form actions outside the exact HTTPS origin. Do not put credentials on the
command line, in environment variables, or in a report.

Success requires a login-denied baseline, followed by a protected response
without that denial and with a same-origin logout link, plus PHPSESSID in the jar.
A failed or inconclusive run does not prove browser extraction is necessary;
credentials, rate limiting, or changed page markers could also be responsible.

## Result — confirmed

On 2026-10-18 the user ran the probe locally with valid credentials and supplied
its non-sensitive JSON summary. The baseline required login; after the credential
POST the protected listing no longer required login and contained a same-origin
logout link. PHPSESSID was present before and after login, and
`plain_http_login_confirmed` was true.

Conclusion: plain HTTPS form login with an in-memory cookie jar works for the
tested account and current site. Browser-cookie extraction is not required for
this flow. The result is user-observed live evidence, not an automated CI login.
No credentials, cookie values, or authenticated page contents were retained.

Card 15 should implement a normal HTTP session: fetch the login form, POST its
credentials/controls, retain cookies, and verify protected content. Do not treat
HTTP 200 or cookie presence alone as success. The current probe supplies evidence
for this design but is not the production client.

Session expiry, invalid-credential behavior, rate limits, secure credential
persistence, and automatic retries remain unverified or separate later work.
Search normalization still needs actual authenticated query/result comparisons;
this successful login alone does not complete card 12. Card 14 is ready for review
and can be marked Done once its research PR is merged.
