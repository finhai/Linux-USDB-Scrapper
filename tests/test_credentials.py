import pytest

from usdb_scrapper.credential_manager import (
    Credentials,
    CredentialStore,
    CredentialStoreError,
    store,
    terminal,
)


class MemoryBackend:
    def __init__(self):
        self.value = None

    def get_password(self, service, account):
        return self.value

    def set_password(self, service, account, value):
        self.value = value

    def delete_password(self, service, account):
        self.value = None


def test_save_reload_and_forget_without_secret_repr(monkeypatch):
    backend = MemoryBackend()
    monkeypatch.setattr(store, "_native_backend", lambda: backend)
    secret = Credentials("test-user", "test-secret")
    assert "test-" not in repr(secret)
    CredentialStore().save(secret)
    assert CredentialStore().load() == secret
    monkeypatch.setattr(terminal.getpass, "getpass", lambda _: pytest.fail("Unexpected prompt"))
    assert terminal.get_credentials() == ("test-user", "test-secret")
    CredentialStore().forget()
    assert CredentialStore().load() is None


def test_unavailable_backend_sanitizes_errors_and_falls_back(monkeypatch):
    def fail():
        raise RuntimeError("sensitive-backend-details")

    monkeypatch.setattr(store, "_native_backend", fail)
    with pytest.raises(CredentialStoreError) as error:
        CredentialStore().save(Credentials("user", "secret"))
    assert "sensitive" not in str(error.value)
    prompts = iter(["user", "secret"])
    monkeypatch.setattr(terminal.getpass, "getpass", lambda _: next(prompts))
    assert terminal.get_credentials() == ("user", "secret")


def test_malformed_stored_secret_is_not_exposed(monkeypatch):
    backend = MemoryBackend()
    backend.value = "sensitive-invalid-json"
    monkeypatch.setattr(store, "_native_backend", lambda: backend)
    with pytest.raises(CredentialStoreError) as error:
        CredentialStore().load()
    assert "sensitive" not in str(error.value)


def test_remembered_provider_degrades_without_keyring():
    from usdb_scrapper.credential_manager.provider import RememberedCredentials
    from usdb_scrapper.credential_manager.store import CredentialStoreError

    class Unavailable:
        def load(self):
            raise CredentialStoreError("unavailable")

    assert RememberedCredentials(Unavailable()).get_credentials() is None
    assert RememberedCredentials(Unavailable(), enabled=False).get_credentials() is None


def test_remembered_login_has_fixed_thirty_day_expiry(monkeypatch):
    backend = MemoryBackend()
    monkeypatch.setattr(store, "_native_backend", lambda: backend)
    now = 1_800_000_000
    monkeypatch.setattr(store.time, "time", lambda: now)
    credentials = Credentials("user", "secret")
    CredentialStore().save(credentials)
    original = backend.value
    expires = now + store.REMEMBER_SECONDS
    assert CredentialStore().load_recent() == (credentials, expires)
    now = expires - 1
    assert CredentialStore().load_recent() == (credentials, expires)
    assert backend.value == original  # Reading never renews the period.
    now = expires
    assert CredentialStore().load_recent() is None


def test_old_or_future_timestamp_requires_manual_login(monkeypatch):
    import json

    backend = MemoryBackend()
    monkeypatch.setattr(store, "_native_backend", lambda: backend)
    monkeypatch.setattr(store.time, "time", lambda: 1000)
    for timestamp in (None, 1001, "1000", True, float("nan")):
        backend.value = json.dumps(
            {"username": "user", "password": "secret", "saved_at": timestamp}
        )
        assert CredentialStore().load_recent() is None
