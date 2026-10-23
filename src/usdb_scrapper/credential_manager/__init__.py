"""Credential provider contract and native storage exports."""

from typing import Protocol

from usdb_scrapper.credential_manager.store import Credentials as Credentials
from usdb_scrapper.credential_manager.store import CredentialStore as CredentialStore
from usdb_scrapper.credential_manager.store import CredentialStoreError as CredentialStoreError


class CredentialProvider(Protocol):
    def get_credentials(self) -> Credentials | None: ...
