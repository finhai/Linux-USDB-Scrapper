"""Worker-owned USDB operations composed from public backend APIs."""

import threading
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, UnidentifiedImageError

from usdb_scrapper.credential_manager import Credentials
from usdb_scrapper.credential_manager.provider import RememberedCredentials
from usdb_scrapper.domain import SongEntry
from usdb_scrapper.parser import ParsedTxt, parse_txt
from usdb_scrapper.usdb_client import (
    DetailClient,
    SearchQuery,
    TxtClient,
    UsdbSession,
    filter_video_results,
    parse_listing,
)


class OperationCancelled(Exception):
    pass


class Gateway:
    def __init__(self, credentials: Credentials, provider: RememberedCredentials) -> None:
        self.credentials = credentials
        self.provider = provider

    def session(self) -> UsdbSession:
        session = UsdbSession(credential_provider=self.provider)
        try:
            session.login(self.credentials.username, self.credentials.password)
        except Exception:
            session.close()
            raise
        return session

    def verify(self) -> None:
        with self.session():
            pass

    @staticmethod
    def pause(cancel: threading.Event, seconds: float) -> None:
        if cancel.wait(seconds):
            raise OperationCancelled()

    def search_page(
        self, query: SearchQuery, offset: int, cancel: threading.Event
    ) -> tuple[tuple[SongEntry, ...], bool]:
        with self.session() as session:
            fields = {**query.form_fields(), "start": str(offset), "limit": "100"}
            entries = parse_listing(session.post_html("/?link=list", fields))
            if len(entries) > 100:
                raise ValueError("Search page exceeded its requested size")
            enriched = []
            details = DetailClient(session)
            for entry in entries:
                self.pause(cancel, 1.0)
                links = details.fetch(entry.song_id).youtube_urls
                enriched.append(replace(entry, youtube_url=links[0] if links else None))
            return filter_video_results(enriched), len(entries) == 100

    def txt(self, song_id: int, cancel: threading.Event) -> ParsedTxt:
        with self.session() as session:
            client = TxtClient(session, pause=lambda seconds: self.pause(cancel, seconds))
            return parse_txt(client.retrieve_text(song_id))

    def cover(self, song_id: int, target: Path, cancel: threading.Event) -> None:
        target.write_bytes(self.cover_bytes(song_id, cancel))

    @staticmethod
    def cover_bytes(song_id: int, cancel: threading.Event) -> bytes:
        # Cover URL is independent of comments and VIDEO meta-tag co/bg fields.
        data = bytearray()
        with httpx.stream(
            "GET",
            f"https://usdb.animux.de/data/cover/{song_id}.jpg",
            timeout=20,
            follow_redirects=False,
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                Gateway.pause(cancel, 0)
                data.extend(chunk)
                if len(data) > 10_000_000:
                    raise ValueError("Cover exceeds the supported size")
        try:
            with Image.open(BytesIO(data)) as image:
                if image.width * image.height > 25_000_000:
                    raise ValueError("Cover dimensions exceed the supported size")
                output = BytesIO()
                image.convert("RGB").save(output, format="JPEG")
                return output.getvalue()
        except (UnidentifiedImageError, OSError):
            raise ValueError("USDB did not return a valid cover image") from None
