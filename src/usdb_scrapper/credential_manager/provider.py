"""Native credential lookup that gracefully degrades without a backend."""

from usdb_scrapper.credential_manager.store import (
    Credentials,
    CredentialStore,
    CredentialStoreError,
)


class RememberedCredentials:
    def __init__(self, store: CredentialStore | None = None, *, enabled: bool = True) -> None:
        self.store = store or CredentialStore()
        self.enabled = enabled

    def get_credentials(self) -> Credentials | None:
        if not self.enabled:
            return None
        try:
            return self.store.load()
        except CredentialStoreError:
            return None
