"""Single-account USDB credentials in an explicitly selected native keyring."""

import json
import sys
from dataclasses import dataclass, field

from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError

SERVICE = "Linux-USDB-Scrapper/USDB"
ACCOUNT = "remembered-account"


class CredentialStoreError(ValueError):
    """Sanitized native-keyring failure."""


@dataclass(frozen=True)
class Credentials:
    username: str = field(repr=False)
    password: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.username, str) or not self.username.strip():
            raise CredentialStoreError("USDB username is missing")
        if not isinstance(self.password, str) or not self.password:
            raise CredentialStoreError("USDB password is missing")


def _native_backend() -> KeyringBackend:
    try:
        if sys.platform == "linux":
            from keyring.backends.SecretService import Keyring

            return Keyring()  # type: ignore[no-untyped-call]  # Upstream constructor lacks annotations.
        if sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring

            return WinVaultKeyring()
    except Exception:
        raise CredentialStoreError("Native credential storage is unavailable") from None
    raise CredentialStoreError("No supported native credential store on this platform")


class CredentialStore:
    """Never auto-select third-party or plaintext keyring backends."""

    def load(self) -> Credentials | None:
        try:
            value = _native_backend().get_password(SERVICE, ACCOUNT)
            if value is None:
                return None
            data = json.loads(value)
            return Credentials(username=data["username"], password=data["password"])
        except Exception:
            raise CredentialStoreError("Remembered credentials could not be read") from None

    def save(self, credentials: Credentials) -> None:
        try:
            _native_backend().set_password(
                SERVICE,
                ACCOUNT,
                json.dumps(
                    {
                        "username": credentials.username,
                        "password": credentials.password,
                    }
                ),
            )
        except Exception:
            raise CredentialStoreError(
                "Credentials could not be saved to the native keyring"
            ) from None

    def forget(self) -> None:
        try:
            _native_backend().delete_password(SERVICE, ACCOUNT)
        except PasswordDeleteError:
            # Only treat confirmed absence as successful deletion.
            if self.load() is not None:
                raise CredentialStoreError("Remembered credentials could not be removed") from None
        except Exception:
            raise CredentialStoreError("Remembered credentials could not be removed") from None
