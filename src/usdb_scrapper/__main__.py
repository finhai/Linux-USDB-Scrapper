"""Application entry point; composition belongs here."""

import argparse
import sys

from usdb_scrapper import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="USDB Scrapper desktop application")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args()
    from PySide6.QtWidgets import QApplication

    from usdb_scrapper.frontend.window import MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("USDB Scrapper")
    app.setApplicationVersion(__version__)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
