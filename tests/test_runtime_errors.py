import threading

import pytest

from usdb_scrapper.controllers.runtime import Runtime


def test_background_failure_is_reported_without_secret_exception_text(caplog):
    notified = threading.Event()
    runtime = Runtime(on_error=notified.set)

    async def failing():
        raise RuntimeError("password=private-token")

    try:
        future = runtime.submit(failing())
        with pytest.raises(RuntimeError):
            future.result(timeout=5)
        assert notified.wait(1)
        assert "Background operation failed" in caplog.text
        assert "private-token" not in caplog.text
        assert all(record.exc_info is None for record in caplog.records)
    finally:
        runtime.stop()
        runtime.thread.join(5)
    assert not runtime.thread.is_alive()
