"""Desktop views; all backend operations pass through ApplicationController."""

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QStackedWidget,
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
    def __init__(
        self, controller: ApplicationController | None = None, *, restore_login: bool = True
    ) -> None:
        super().__init__()
        self.controller = controller or ApplicationController()
        self.setWindowTitle("USDB Scrapper")
        self.setStyleSheet(PURPLE_THEME)
        self._cover_icons: dict[int, QIcon] = {}
        self.resize(1100, 720)
        self._songs: list[SongEntry] = []
        self._jobs: tuple[DownloadItem, ...] = ()
        self._adding: set[int] = set()
        self._busy = False
        self._more = False
        self._page_received = False
        self._page_failed = False
        self._closing = False
        self._stopped = False
        self._sort_field = self.controller.settings.sort_field
        self._direction = self.controller.settings.sort_direction
        self.tabs = QTabWidget()
        self.pages = QStackedWidget()
        self.setCentralWidget(self.pages)
        self._build_search()
        self._build_downloads()
        self._build_settings()
        self._build_login()
        self.pages.addWidget(self.tabs)
        self.pages.setCurrentWidget(self.login_page)
        self.controller.results.connect(self._results)
        self.controller.search_reset.connect(self._reset_search)
        self.controller.search_failed.connect(self._search_failed)
        self.controller.source_checked.connect(self._source_checked)
        self.controller.cover_ready.connect(self._cover_ready)
        self.controller.downloads.connect(self._downloads)
        self.controller.enqueue_result.connect(self._enqueue_result)
        self.controller.message.connect(self._message)
        self.controller.busy.connect(self._set_busy)
        self.controller.login_required.connect(self._show_login)
        self.controller.login_complete.connect(self._login_complete)
        self.controller.stopped.connect(self._on_stopped)
        self.controller.settings_changed.connect(self._settings_changed)
        self.statusBar().showMessage(self.controller.startup_message or "Sign in to USDB to begin.")

        if restore_login:
            self.login_button.setEnabled(False)
            self.login_status.setText("Checking saved login…")
            QTimer.singleShot(0, self.controller.restore_login)

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
        self.search_status = QLabel(
            "Search by artist, title, or both. Media sources are checked separately."
        )
        layout.addWidget(self.search_status)
        self.results_table = self._table(
            [
                "Cover",
                "ID",
                "Artist",
                "Title",
                "Language",
                "Year",
                "Download status",
                "Source check",
            ]
        )
        self.results_table.setColumnWidth(0, 90)
        self.results_table.setColumnWidth(1, 60)
        self.results_table.setColumnWidth(2, 190)
        self.results_table.setColumnWidth(3, 230)
        self.results_table.setColumnWidth(4, 110)
        self.results_table.setColumnWidth(5, 60)
        self.results_table.setColumnWidth(6, 145)
        bar = self.results_table.verticalScrollBar()
        bar.valueChanged.connect(self._scroll)
        layout.addWidget(self.results_table)
        actions = QHBoxLayout()
        self.more_button = QPushButton("Retry loading results")
        self.more_button.hide()
        self.more_button.setEnabled(False)
        self.more_button.clicked.connect(self.controller.load_more)
        self.download_button = QPushButton("Add to queue")
        self.download_button.setObjectName("primary")
        self.download_button.clicked.connect(self._enqueue)
        self.download_button.setEnabled(False)
        self.results_table.itemSelectionChanged.connect(self._refresh_queue_status)
        actions.addWidget(self.more_button)
        self.refresh_button = QPushButton("Refresh results")
        self.refresh_button.clicked.connect(lambda: self._search(refresh=True))
        actions.addWidget(self.refresh_button)
        self.cancel_search_button = QPushButton("Cancel search")
        self.cancel_search_button.clicked.connect(self.controller.cancel_search)
        self.cancel_search_button.setEnabled(False)
        actions.addWidget(self.cancel_search_button)
        actions.addStretch()
        actions.addWidget(self.download_button)
        layout.addLayout(actions)
        self.queue_feedback = QLabel("Select songs to add to the download queue.")
        self.queue_feedback.setWordWrap(True)
        layout.addWidget(self.queue_feedback)
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

    def _search(self, *, refresh: bool = False) -> None:
        if not self.artist.text().strip() and not self.title.text().strip():
            self.search_status.setText("Enter an artist or song title.")
            return
        self._busy = True
        self.cancel_search_button.setEnabled(True)
        self.search_status.setText("Starting search…")
        self.controller.search(
            self.artist.text(),
            self.title.text(),
            self._sort_field,
            self._direction,
            refresh=refresh,
        )

    def _reset_search(self) -> None:
        self._songs.clear()
        self.results_table.setRowCount(0)
        self._more = False
        self._page_failed = False
        self.more_button.hide()
        self._refresh_queue_status()

    def _search_failed(self, message: str) -> None:
        self._page_failed = True
        self.search_status.setText(message)
        self.more_button.setEnabled(True)
        self.more_button.show()

    def _source_checked(self, song_id: int, status: str) -> None:
        for row, song in enumerate(self._songs):
            if song.song_id == song_id:
                cell = self.results_table.item(row, 7)
                if cell is not None:
                    cell.setText(status)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.cancel_search_button.setEnabled(busy or bool(self._songs))
        if busy:
            self._page_failed = False
            self.more_button.hide()
            self.search_status.setText("Loading more songs…" if self._songs else "Searching…")
        elif not self._page_failed:
            self.search_status.setText(
                f"{len(self._songs)} songs loaded · Scroll down for more"
                if self._more
                else f"All results loaded ({len(self._songs)})"
            )
        if (
            not busy
            and not self._page_failed
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
            source = QTableWidgetItem("Not checked")
            source.setToolTip(
                "Comment links are checked in the background. TXT media metadata and actual "
                "download availability are verified when downloading."
            )
            self.results_table.setItem(row, 7, source)
            self._songs.append(song)
            self._set_cover(self.results_table, row, song.song_id)
        self._refresh_queue_status()

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
            and not self._page_failed
            and not self._busy
            and value >= self.results_table.verticalScrollBar().maximum()
        ):
            self.controller.load_more()

    def _refresh_queue_status(self) -> None:
        states = {job.song.song_id: job.state.value for job in self._jobs}
        for row, song in enumerate(self._songs):
            state = states.get(song.song_id, "Adding…" if song.song_id in self._adding else "")
            cell = self.results_table.item(row, 6)
            if cell is None:
                cell = QTableWidgetItem()
                self.results_table.setItem(row, 6, cell)
            cell.setText(state.capitalize())
            cell.setForeground(QColor("#72dfc0"))
        rows = {index.row() for index in self.results_table.selectedIndexes()}
        available = sum(
            1
            for row in rows
            if row < len(self._songs)
            and self._songs[row].song_id not in states
            and self._songs[row].song_id not in self._adding
        )
        self.download_button.setEnabled(available > 0)
        self.download_button.setText(
            f"Add {available} to queue"
            if available
            else "Adding…"
            if self._adding
            else "Already in Downloads"
            if rows
            else "Add to queue"
        )

    def _enqueue(self) -> None:
        rows = sorted({index.row() for index in self.results_table.selectedIndexes()})
        known = {job.song.song_id for job in self._jobs} | self._adding
        songs = [self._songs[row] for row in rows if self._songs[row].song_id not in known]
        if not songs:
            return
        self._adding.update(song.song_id for song in songs)
        self.queue_feedback.setText(f"Adding {len(songs)} to queue…")
        self._refresh_queue_status()
        self.controller.enqueue(songs)

    def _enqueue_result(self, requested: list[int], message: str) -> None:
        self._adding.difference_update(requested)
        self.queue_feedback.setText(message)
        self.statusBar().showMessage(message)
        self._refresh_queue_status()

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
        self.tabs.setTabText(1, f"Downloads ({len(jobs)})")
        self._refresh_queue_status()
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
        save = QPushButton("Save settings")
        save.clicked.connect(self._save_settings)
        form.addRow(save)
        forget = QPushButton("Forget saved credentials")
        forget.clicked.connect(self.controller.forget_credentials)
        form.addRow(forget)
        note = QLabel(
            "Release packages include the media download tools.\n"
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
            self.controller.settings.remember,
        )

    def _build_login(self) -> None:
        self.login_page = QWidget()
        layout = QVBoxLayout(self.login_page)
        layout.addStretch()
        card = QWidget()
        card.setMaximumWidth(440)
        form = QFormLayout(card)
        heading = QLabel("Welcome to USDB Scrapper")
        heading.setStyleSheet("font-size: 24px; font-weight: bold; color: #d4b0ff;")
        form.addRow(heading)
        description = QLabel("Sign in with your USDB account to search and download songs.")
        description.setWordWrap(True)
        form.addRow(description)
        self.username = QLineEdit()
        self.username.setPlaceholderText("USDB username")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.returnPressed.connect(self._login)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        self.login_remember = QCheckBox("Remember me for 30 days")
        self.login_remember.setChecked(self.controller.settings.remember)
        form.addRow(self.login_remember)
        self.login_status = QLabel("Sign in to your USDB account.")
        self.login_status.setWordWrap(True)
        form.addRow(self.login_status)
        self.login_button = QPushButton("Sign in")
        self.login_button.setObjectName("primary")
        self.login_button.clicked.connect(self._login)
        form.addRow(self.login_button)
        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        self.pages.addWidget(self.login_page)

    def _message(self, message: str) -> None:
        self.statusBar().showMessage(message)
        if self.pages.currentWidget() is self.login_page:
            self.login_status.setText(message)

    def _show_login(self) -> None:
        if not self._closing:
            self.login_button.setEnabled(True)
            self.login_button.setText("Sign in")
            self.pages.setCurrentWidget(self.login_page)
            if self.login_status.text() == "Checking saved login…":
                self.login_status.setText("Sign in to your USDB account.")
            self.password.setFocus()

    def _login(self) -> None:
        if not self.login_button.isEnabled():
            return
        if not self.username.text().strip() or not self.password.text():
            self.login_status.setText("Enter your username and password.")
            return
        self.login_button.setEnabled(False)
        self.login_button.setText("Signing in…")
        self.login_status.setText("Connecting to USDB…")
        self.controller.login(
            self.username.text(), self.password.text(), self.login_remember.isChecked()
        )
        self.password.clear()

    def _login_complete(self) -> None:
        self.password.clear()
        self.login_button.setEnabled(True)
        self.login_button.setText("Sign in")
        self.pages.setCurrentWidget(self.tabs)
        self.statusBar().showMessage("Signed in. Search for songs to get started.")

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
