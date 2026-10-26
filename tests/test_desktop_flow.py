"""Drive real Qt views/controller with offline external-service replacements."""

import os
import subprocess
import sys


def test_login_search_download_settings_and_shutdown(tmp_path):
    script = r"""
import asyncio
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
import usdb_scrapper.controllers.application as module
from usdb_scrapper.domain import SongEntry
from usdb_scrapper.parser import parse_txt
from usdb_scrapper.storage_manager.settings import SettingsStore, Settings
from usdb_scrapper.frontend.window import MainWindow

class Store:
    def load(self): return None
    def load_recent(self): return None
    def save(self, credentials): pass
    def forget(self): pass
class Provider:
    def __init__(self, **kwargs): pass
    def get_credentials(self): raise AssertionError("Desktop must never load saved credentials")
class Gateway:
    def __init__(self, credentials, provider): pass
    def verify(self): pass
    @staticmethod
    def cover_bytes(song_id, cancel):
        from PIL import Image
        from io import BytesIO
        output = BytesIO()
        Image.new('RGB', (32, 32), '#8452d4').save(output, format='JPEG')
        return output.getvalue()
    def search_page(self, query, offset, cancel):
        assert query.artist == 'artist'
        return (SongEntry(song_id=1, artist='Artist', title='Song',
                          youtube_url='https://www.youtube.com/watch?v=abcdefghijk'),), False
    def txt(self, song_id, cancel):
        return parse_txt('#TITLE:Song\n#ARTIST:Artist\n#BPM:120\n#MP3:old.mp3\n'
                         '#VIDEO:v=abcdefghijk\n: 0 4 2 notes\nE\n'.replace('\\n', '\n'))
    def cover(self, song_id, target, cancel): target.write_bytes(b'cover fixture')
class Media:
    async def audio(self, url, target): target.write_bytes(b'audio fixture')
    async def video(self, url, target): target.write_bytes(b'video fixture')
module.Gateway = Gateway
module.YtDlpDownloader = Media
module.CredentialStore = Store
module.RememberedCredentials = Provider
app = QApplication([])
store = SettingsStore(Path('config.json'))
store.save(Settings(storage_root=str(Path('library').resolve())))
controller = module.ApplicationController(store)
window = MainWindow(controller)
window.show()
assert window.pages.currentWidget() is window.login_page
assert not window.tabs.isVisible()
window.artist.setText('Artist')
phase = 0
errors = []

def poll():
    global phase
    try:
        if (phase == 0 and window.pages.currentWidget() is window.login_page
                and window.login_button.isEnabled()):
            window.username.setText('demo')
            window.password.setText('synthetic')
            window._login()
            phase = 10
        elif phase == 10 and window.pages.currentWidget() is window.tabs:
            window.search_button.click()
            phase = 1
        elif phase == 1 and window.results_table.rowCount() == 1:
            assert window.password.text() == ''
            window.results_table.selectRow(0)
            window.download_button.click()
            assert not window.download_button.isEnabled()
            assert window.results_table.item(0, 6).text() == 'Adding…'
            window.download_button.click()  # A second click must not submit again.
            phase = 2
        elif phase == 2 and window._jobs and window._cover_icons:
            assert len(window._jobs) == 1
            assert window._jobs[0].state.value == 'queued'
            assert window.results_table.item(0, 6).text() == 'Queued'
            assert not window.download_button.isEnabled()
            assert window.download_button.text() == 'Already in Downloads'
            assert window.tabs.tabText(1) == 'Downloads (1)'
            assert 'Added 1 to queue' in window.queue_feedback.text()
            assert not Path(window._jobs[0].bundle.txt).exists()
            window.start_button.click()
            phase = 20
        elif phase == 20 and window._jobs[0].state.value in ('completed', 'failed'):
            assert window._jobs[0].state.value == 'completed', window._jobs[0]
            directory = Path(window._jobs[0].bundle.txt).parent
            assert len(list(directory.iterdir())) == 4
            text = Path(window._jobs[0].bundle.txt).read_text()
            assert '#VERSION:1.0.0' in text and '#AUDIO:Song.mp3' in text
            assert 'youtube' not in text
            assert Path(window._jobs[0].bundle.cover).read_bytes() == Gateway.cover_bytes(1, None)
            window.concurrency.setValue(3)
            window._save_settings()
            phase = 3
        elif phase == 3 and controller.settings.concurrency == 3:
            assert store.load().concurrency == 3
            window.close()
            phase = 4
    except Exception as exc:
        errors.append(repr(exc))
        window.close()

timer = QTimer()
timer.timeout.connect(poll)
timer.start(10)
QTimer.singleShot(10000, window.close)
app.exec()
controller.runtime.thread.join(5)
assert not controller.runtime.thread.is_alive()
assert not errors, errors
assert phase == 4, phase
"""
    # Keep the embedded fixture's line breaks interpreted by its Python string.
    script = script.replace("\\\\n", "\\n")
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        check=True,
        timeout=20,
    )


def test_views_do_not_import_backend_services():
    import ast
    from pathlib import Path

    root = Path(__file__).parents[1] / "src/usdb_scrapper/frontend"
    forbidden = {
        "usdb_client",
        "parser",
        "download_manager",
        "storage_manager",
        "credential_manager",
    }
    for path in root.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert not forbidden.intersection((node.module or "").split(".")), path
