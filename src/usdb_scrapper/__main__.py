"""Application entry point; composition belongs here."""

import argparse
import sys

from usdb_scrapper import __version__


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--media-worker":
        # External FFmpeg must use host libraries, not PyInstaller's Qt libraries.
        import os

        import yt_dlp  # type: ignore[import-untyped]  # Upstream does not ship type metadata.

        if getattr(sys, "frozen", False):
            if sys.platform == "win32":
                import ctypes

                ctypes.windll.kernel32.SetDllDirectoryW(None)
            elif "LD_LIBRARY_PATH_ORIG" in os.environ:
                os.environ["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH_ORIG"]
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)
        yt_dlp.main(sys.argv[2:])
        return 0
    parser = argparse.ArgumentParser(description="USDB Scrapper desktop application")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    import logging

    # Configure only our namespace; HTTP libraries must not log request metadata.
    app_logger = logging.getLogger("usdb_scrapper")
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    from PySide6.QtWidgets import QApplication

    from usdb_scrapper.frontend.window import MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("USDB Scrapper")
    app.setApplicationVersion(__version__)
    window = MainWindow(restore_login=not args.smoke_test)
    window.show()
    if args.smoke_test:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(500, window.close)
    result = app.exec()
    # Destroy Qt objects while Python callbacks and wrappers are still alive.
    from PySide6.QtCore import QCoreApplication, QEvent

    window.controller.deleteLater()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
