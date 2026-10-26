"""Explicitly save, verify or forget USDB credentials; never print their values."""

import argparse
import getpass
import json
import sys

from usdb_scrapper.credential_manager import Credentials, CredentialStore, CredentialStoreError
from usdb_scrapper.usdb_client import UsdbError, UsdbSession


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("save", "check", "forget"), nargs="?", default="save")
    action = parser.parse_args().action
    if not sys.stdin.isatty():
        print("Run in your own terminal.")
        return 2
    try:
        store = CredentialStore()
        if action == "forget":
            store.forget()
            print(json.dumps({"forgotten": True}))
            return 0
        if action == "save":
            # Check keyring access before asking for secrets or sending login requests.
            store.load()
            credentials = Credentials(
                getpass.getpass("USDB username (hidden): "),
                getpass.getpass("USDB password (hidden): "),
            )
        else:
            credentials = store.load()
            if credentials is None:
                print(json.dumps({"remembered": False}))
                return 1
        with UsdbSession() as session:
            session.login(credentials.username, credentials.password)
        if action == "save":
            store.save(credentials)
            if store.load() != credentials:
                raise CredentialStoreError("Stored credential verification failed")
        print(json.dumps({"remembered": True, "login_verified": True}))
        return 0
    except (CredentialStoreError, UsdbError) as exc:
        print(json.dumps({"success": False, "error": str(exc)}))
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Cancelled.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
