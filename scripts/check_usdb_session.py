"""Manual real-site acceptance check for the production session client."""

import json
import sys

from usdb_scrapper.credential_manager.terminal import get_credentials
from usdb_scrapper.usdb_client import UsdbError, UsdbSession


def main():
    if not sys.stdin.isatty():
        print("Run in your own terminal; do not pipe credentials.")
        return 2
    try:
        username, password = get_credentials()
        with UsdbSession() as session:
            session.login(username, password)
            username = password = ""
            html = session.get_html()
            print(
                json.dumps(
                    {
                        "login_verified": session.authenticated,
                        "subsequent_request_succeeded": bool(html),
                    },
                    indent=2,
                )
            )
        return 0
    except (UsdbError, ValueError) as exc:
        print(f"Check failed: {exc}")
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Check cancelled.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
