"""Desktop views; all backend operations pass through ApplicationController."""

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from usdb_scrapper.controllers.application import ApplicationController
from usdb_scrapper.domain import SongEntry
from usdb_scrapper.domain.download_item import DownloadItem, DownloadState
from usdb_scrapper.frontend.theme import PURPLE_THEME

SORTS = (
    ("Song ID", "id"),
    ("Artist", "interpret"),
    ("Title", "title"),
    ("Genre", "genre"),
    ("Year", "year"),
    ("Edition", "edition"),
    ("Golden notes", "golden"),
    ("Language", "language"),
    ("Creator", "autor"),
    ("Rating", "rating"),
    ("Views", "views"),
    ("Last changed", "lastchange"),
)


class MainWindow(QMainWindow):
    def __init__(self, controller: ApplicationController | None = None) -> None:
        super().__init__()
        self.controller = controller or ApplicationController()
        self.setWindowTitle("USDB Scrapper")
        self.setStyleSheet(PURPLE_THEME)
        self._cover_icons: dict[int, QIcon] = {}
        self.resize(1100, 720)
        self._songs: list[SongEntry] = []
        self._jobs: tuple[DownloadItem, ...] = ()
        self._busy = False
        self._more = False
        self._page_received = False
        self._closing = False
        self._stopped = False
        self._sort_field = self.controller.settings.sort_field
        self._direction = self.controller.settings.sort_direction
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_search()
        self._build_downloads()
        self._build_settings()
        self._build_login()
        self.controller.results.connect(self._results)
        self.controller.cover_ready.connect(self._cover_ready)
        self.controller.downloads.connect(self._downloads)
        self.controller.message.connect(self.statusBar().showMessage)
        self.controller.busy.connect(self._set_busy)
        self.controller.login_required.connect(self._show_login)
        self.controller.login_complete.connect(self._login_complete)
        self.controller.stopped.connect(self._on_stopped)
        self.controller.settings_changed.connect(self._settings_changed)
        self.statusBar().showMessage(
            self.controller.startup_message or "Ready — sign in when you search."
        )

    @staticmethod
    def _table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().hide()
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setIconSize(QSize(64, 64))
        table.verticalHeader().setDefaultSectionSize(82)
        return table

    def _build_search(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        heading = QLabel("Find songs on USDB")
        heading.setStyleSheet("font-size: 24px; font-weight: 600; padding: 12px 0;")
        layout.addWidget(heading)
        row = QHBoxLayout()
        self.artist = QLineEdit()
        self.artist.setPlaceholderText("Artist")
        self.title = QLineEdit()
        self.title.setPlaceholderText("Song title")
        self.search_button = QPushButton("Search")
        self.search_button.setObjectName("primary")
        self.search_button.clicked.connect(self._search)
        self.artist.returnPressed.connect(self._search)
        self.title.returnPressed.connect(self._search)
        self.sort = QComboBox()
        for name, value in SORTS:
            self.sort.addItem(name, value)
        self.sort.setCurrentIndex(self.sort.findData(self._sort_field))
        self.sort.activated.connect(self._select_sort)
        self.sort_direction = QLabel(self._direction.upper())
        for widget in (self.artist, self.title, self.sort, self.sort_direction, self.search_button):
            row.addWidget(widget)
        layout.addLayout(row)
        self.search_status = QLabel("Results include only songs with a supported YouTube link.")
        layout.addWidget(self.search_status)
        self.results_table = self._table(["Cover", "ID", "Artist", "Title", "Language", "Year"])
        self.results_table.setColumnWidth(0, 90)
        self.results_table.setColumnWidth(1, 80)
        self.results_table.setColumnWidth(2, 240)
        self.results_table.setColumnWidth(3, 350)
        bar = self.results_table.verticalScrollBar()
        bar.valueChanged.connect(self._scroll)
        layout.addWidget(self.results_table)
        actions = QHBoxLayout()
        self.more_button = QPushButton("Load more")
        self.more_button.setEnabled(False)
        self.more_button.clicked.connect(self.controller.load_more)
        self.download_button = QPushButton("Add to queue")
        self.download_button.setObjectName("primary")
        self.download_button.clicked.connect(self._enqueue)
        actions.addWidget(self.more_button)
        actions.addStretch()
        actions.addWidget(self.download_button)
        layout.addLayout(actions)
        self.tabs.addTab(page, "Search")

    def _select_sort(self, index: int) -> None:
        field = str(self.sort.itemData(index))
        self._direction = (
            "desc" if field == self._sort_field and self._direction == "asc" else "asc"
        )
        self._sort_field = field
        self.sort_direction.setText(self._direction.upper())
        if self.artist.text().strip() or self.title.text().strip():
            self._search()

    def _search(self) -> None:
        if not self._busy:
            self._songs.clear()
            self.results_table.setRowCount(0)
            self.controller.search(
                self.artist.text(), self.title.text(), self._sort_field, self._direction
            )

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.search_button.setEnabled(not busy)
        self.sort.setEnabled(not busy)
        self.more_button.setEnabled(self._more and not busy)
        self.search_status.setText(
            "Searching and checking YouTube links…" if busy else f"{len(self._songs)} songs loaded"
        )
        if (
            not busy
            and self._page_received
            and self._more
            and self.results_table.verticalScrollBar().maximum() == 0
        ):
            QTimer.singleShot(0, self.controller.load_more)
        if not busy:
            self._page_received = False

    def _results(self, entries: tuple[SongEntry, ...], more: bool) -> None:
        self._more = more
        self._page_received = True
        for song in entries:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            for column, value in enumerate(
                ("♫", song.song_id, song.artist, song.title, song.language or "", song.year or "")
            ):
                self.results_table.setItem(row, column, QTableWidgetItem(str(value)))
            self._songs.append(song)
            self._set_cover(self.results_table, row, song.song_id)
        self.more_button.setEnabled(more and not self._busy)

    def _set_cover(self, table: QTableWidget, row: int, song_id: int) -> None:
        cell = table.item(row, 0)
        if cell is None:
            return
        if song_id in self._cover_icons:
            cell.setText("")
            cell.setIcon(self._cover_icons[song_id])
        else:
            cell.setToolTip("Cover unavailable or loading")

    def _cover_ready(self, song_id: int, data: bytes) -> None:
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return
        self._cover_icons[song_id] = QIcon(
            pixmap.scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        for row, song in enumerate(self._songs):
            if song.song_id == song_id:
                self._set_cover(self.results_table, row, song_id)
        for row, item in enumerate(self._jobs):
            if item.song.song_id == song_id:
                self._set_cover(self.downloads_table, row, song_id)

    def _scroll(self, value: int) -> None:
        if (
            self._more
            and not self._busy
            and value >= self.results_table.verticalScrollBar().maximum()
        ):
            self.controller.load_more()

    def _enqueue(self) -> None:
        rows = sorted({index.row() for index in self.results_table.selectedIndexes()})
        self.controller.enqueue([self._songs[row] for row in rows])
        if rows:
            self.statusBar().showMessage(
                f"Added {len(rows)} selected songs. Open Downloads to start the queue."
            )

    def _build_downloads(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Build your queue, then start downloads when you are ready."))
        self.downloads_table = self._table(
            ["Cover", "ID", "Artist", "Title", "State", "Progress / error"]
        )
        self.downloads_table.setColumnWidth(0, 90)
        self.downloads_table.setColumnWidth(2, 230)
        self.downloads_table.setColumnWidth(3, 300)
        layout.addWidget(self.downloads_table)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel selected")
        retry = QPushButton("Retry selected")
        cancel.clicked.connect(lambda: self._download_action(False))
        retry.clicked.connect(lambda: self._download_action(True))
        self.start_button = QPushButton("Start queued downloads")
        self.start_button.setObjectName("start")
        self.start_button.clicked.connect(self.controller.start_downloads)
        row.addWidget(self.start_button)
        row.addWidget(cancel)
        row.addWidget(retry)
        row.addStretch()
        layout.addLayout(row)
        self.tabs.addTab(page, "Downloads")

    def _downloads(self, jobs: tuple[DownloadItem, ...], stages: dict[int, str]) -> None:
        selected = {
            self._jobs[i.row()].song.song_id
            for i in self.downloads_table.selectedIndexes()
            if i.row() < len(self._jobs)
        }
        self._jobs = jobs
        self.start_button.setEnabled(any(job.state is DownloadState.QUEUED for job in jobs))
        self.downloads_table.setRowCount(len(jobs))
        for row, item in enumerate(jobs):
            state = item.state
            detail = item.error or (
                stages.get(item.song.song_id, "Starting")
                if state is DownloadState.DOWNLOADING
                else ""
            )
            for column, value in enumerate(
                ("♫", item.song.song_id, item.song.artist, item.song.title, state.value, detail)
            ):
                cell = QTableWidgetItem(str(value))
                if column == 4:
                    cell.setForeground(
                        QColor(
                            {
                                DownloadState.COMPLETED: "#72dfc0",
                                DownloadState.FAILED: "#ff8fa4",
                                DownloadState.DOWNLOADING: "#d4b0ff",
                                DownloadState.QUEUED: "#efcc7c",
                            }.get(state, "#b9adca")
                        )
                    )
                self.downloads_table.setItem(row, column, cell)
                cell.setSelected(item.song.song_id in selected)
            self._set_cover(self.downloads_table, row, item.song.song_id)

    def _download_action(self, retry: bool) -> None:
        for row in {index.row() for index in self.downloads_table.selectedIndexes()}:
            action = self.controller.retry if retry else self.controller.cancel
            action(self._jobs[row].song.song_id)

    def _build_settings(self) -> None:
        page = QWidget()
        form = QFormLayout(page)
        self.root = QLineEdit(self.controller.settings.storage_root)
        browse = QPushButton("Choose folder…")
        browse.clicked.connect(self._choose_root)
        root_row = QHBoxLayout()
        root_row.addWidget(self.root)
        root_row.addWidget(browse)
        form.addRow("Library location", root_row)
        self.concurrency = QSpinBox()
        self.concurrency.setRange(1, 8)
        self.concurrency.setValue(self.controller.settings.concurrency)
        form.addRow("Concurrent downloads", self.concurrency)
        self.default_sort = QComboBox()
        for name, value in SORTS:
            self.default_sort.addItem(name, value)
        self.default_sort.setCurrentIndex(self.default_sort.findData(self._sort_field))
        form.addRow("Default sort", self.default_sort)
        self.default_direction = QComboBox()
        self.default_direction.addItems(["asc", "desc"])
        self.default_direction.setCurrentText(self._direction)
        form.addRow("Default direction", self.default_direction)
        self.remember = QCheckBox("Use native keyring to remember credentials")
        self.remember.setChecked(self.controller.settings.remember)
        form.addRow(self.remember)
        save = QPushButton("Save settings")
        save.clicked.connect(self._save_settings)
        form.addRow(save)
        forget = QPushButton("Forget saved credentials")
        forget.clicked.connect(self.controller.forget_credentials)
        form.addRow(forget)
        note = QLabel(
            "Downloads require yt-dlp, FFmpeg and ffprobe on PATH.\n"
            "TXT export uses VERSION 1.0.0 with AUDIO headers and original timing."
        )
        note.setWordWrap(True)
        form.addRow(note)
        self.tabs.addTab(page, "Settings")

    def _settings_changed(self) -> None:
        settings = self.controller.settings
        self._sort_field, self._direction = settings.sort_field, settings.sort_direction
        self.sort.setCurrentIndex(self.sort.findData(self._sort_field))
        self.sort_direction.setText(self._direction.upper())
        self.root.setText(settings.storage_root)
        self.concurrency.setValue(settings.concurrency)
        self.default_sort.setCurrentIndex(self.default_sort.findData(settings.sort_field))
        self.default_direction.setCurrentText(settings.sort_direction)
        self.remember.setChecked(settings.remember)
        self.login_remember.setChecked(settings.remember)

    def _choose_root(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Choose library location", self.root.text()
        )
        if selected:
            self.root.setText(selected)

    def _save_settings(self) -> None:
        self.controller.save_settings(
            self.root.text(),
            self.concurrency.value(),
            str(self.default_sort.currentData()),
            self.default_direction.currentText(),
            self.remember.isChecked(),
        )

    def _build_login(self) -> None:
        self.login_dialog = QDialog(self)
        self.login_dialog.setWindowTitle("Sign in to USDB")
        form = QFormLayout(self.login_dialog)
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_remember = QCheckBox("Remember in native keyring")
        self.login_remember.setChecked(self.controller.settings.remember)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        form.addRow(self.login_remember)
        self.login_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.login_buttons.accepted.connect(self._login)
        self.login_buttons.rejected.connect(self.login_dialog.reject)
        self.login_dialog.rejected.connect(self.password.clear)
        form.addRow(self.login_buttons)

    def _show_login(self) -> None:
        if not self._closing:
            self.login_buttons.setEnabled(True)
            self.login_dialog.open()

    def _login(self) -> None:
        self.login_buttons.setEnabled(False)
        self.controller.login(
            self.username.text(), self.password.text(), self.login_remember.isChecked()
        )
        self.password.clear()

    def _login_complete(self) -> None:
        self.password.clear()
        self.login_buttons.setEnabled(True)
        self.login_dialog.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._stopped:
            event.accept()
            return
        event.ignore()
        if not self._closing:
            self._closing = True
            self.setEnabled(False)
            self.statusBar().showMessage("Stopping background work and cleaning partial downloads…")
            self.controller.shutdown()

    def _on_stopped(self) -> None:
        if self.controller.runtime.thread.is_alive():
            QTimer.singleShot(50, self._on_stopped)
            return
        self._stopped = True
        self.close()
