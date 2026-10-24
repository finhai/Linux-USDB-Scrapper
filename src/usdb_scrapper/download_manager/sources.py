"""Compose TXT, media and cover retrieval without coupling to yt-dlp."""

from collections.abc import Awaitable, Callable
from pathlib import Path

from usdb_scrapper.download_manager.media import MediaDownloader
from usdb_scrapper.parser import ParsedTxt


class DownloadSources:
    def __init__(
        self,
        txt: Callable[[int], Awaitable[ParsedTxt]],
        media: MediaDownloader,
        cover: Callable[[ParsedTxt, Path], Awaitable[None]],
    ) -> None:
        self._txt = txt
        self._media = media
        self._cover = cover

    async def fetch_txt(self, song_id: int) -> ParsedTxt:
        return await self._txt(song_id)

    async def fetch_audio(self, song: ParsedTxt, target: Path) -> None:
        await self._media.audio(song.audio_source or song.song.video, target)

    async def fetch_video(self, song: ParsedTxt, target: Path) -> None:
        await self._media.video(song.song.video, target)

    async def fetch_cover(self, song: ParsedTxt, target: Path) -> None:
        await self._cover(song, target)
