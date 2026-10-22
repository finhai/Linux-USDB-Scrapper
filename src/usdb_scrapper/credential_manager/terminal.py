"""Credential selection shared by manual checks; never saves implicitly."""

import getpass

from usdb_scrapper.credential_manager import CredentialStore, CredentialStoreError


def get_credentials() -> tuple[str, str]:
    try:
        stored = CredentialStore().load()
    except CredentialStoreError:
        print("System keyring unavailable or locked; using hidden prompts for this run.")
        stored = None
    if stored is not None:
        return stored.username, stored.password
    return (
        getpass.getpass("USDB username (hidden): "),
        getpass.getpass("USDB password (hidden): "),
    )
