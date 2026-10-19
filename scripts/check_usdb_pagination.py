"""Run production pagination with hidden credentials and a bounded search."""

import getpass
import json
import sys

from usdb_scrapper.usdb_client import PagedSearchClient, SearchQuery, UsdbError, UsdbSession


def main():
    if not sys.stdin.isatty():
        print("Run in your own terminal; do not pipe credentials.")
        return 2
    try:
        username = getpass.getpass("USDB username (hidden): ")
        password = getpass.getpass("USDB password (hidden): ")
        with UsdbSession() as session:
            session.login(username, password)
            username = password = ""
            entries = PagedSearchClient(session).search(SearchQuery(title="Love"), max_pages=50)
        ids = [entry.song_id for entry in entries]
        print(
            json.dumps(
                {
                    "completed": True,
                    "record_count": len(entries),
                    "more_than_100": len(entries) > 100,
                    "unique_ids": len(ids) == len(set(ids)),
                    "ids_ascending": ids == sorted(ids),
                    "all_records_have_artist_and_title": all(e.artist and e.title for e in entries),
                    "first_ids": ids[:5],
                    "last_ids": ids[-5:],
                },
                indent=2,
            )
        )
        return 0
    except (UsdbError, ValueError) as exc:
        print(f"Pagination check failed: {exc}")
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Check cancelled.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
