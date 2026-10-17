"""Minimal launchable shell; feature screens come in later milestones."""

from PySide6.QtWidgets import QLabel, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("USDB Scrapper")
        self.resize(900, 600)
        self.setCentralWidget(QLabel("USDB Scrapper — development foundation"))
