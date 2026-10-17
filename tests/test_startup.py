"""Exercise the installed command and an actual Qt window without a display."""

import os
import subprocess
import sys
from importlib.metadata import version


def test_version_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "usdb_scrapper", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == version("usdb-scrapper-linux")


def test_window_starts_and_exits() -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from usdb_scrapper.frontend.window import MainWindow
app = QApplication([])
window = MainWindow()
window.show()
assert window.isVisible()
QTimer.singleShot(0, app.quit)
assert app.exec() == 0
""",
        ],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=20,
        check=True,
    )
