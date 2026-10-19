"""Credential-provider contract; persistent OS storage is a separate feature."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Credentials:
    username: str = field(repr=False)
    password: str = field(repr=False)


class CredentialProvider(Protocol):
    def get_credentials(self) -> Credentials | None:
        """Return available credentials, or None without prompting the user."""
        ...
