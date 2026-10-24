"""Library path policy; semantic names never become filesystem paths directly."""

from pathlib import Path

from usdb_scrapper.domain import SongEntry
from usdb_scrapper.domain.download_item import DownloadBundle
from usdb_scrapper.normalization.filesystem import readable_filesystem_name


class Library:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def bundle(self, song: SongEntry) -> DownloadBundle:
        artist = readable_filesystem_name(song.artist)
        title = readable_filesystem_name(song.title)
        directory = self.root / artist / title
        # Never follow an existing artist/song symlink outside the selected root.
        if directory.resolve().is_relative_to(self.root) is False:
            raise ValueError("Library target escapes the configured root")
        return DownloadBundle(
            txt=directory / f"{title}.txt",
            audio=directory / f"{title}.mp3",
            video=directory / f"{title}.mp4",
            cover=directory / f"{title}.jpg",
        )

    def recover(self) -> int:
        from usdb_scrapper.storage_manager.bundle import recover_directory

        count = 0
        if self.root.exists():
            for artist in self.root.iterdir():
                if artist.is_dir() and not artist.is_symlink():
                    count += recover_directory(artist)
        return count
