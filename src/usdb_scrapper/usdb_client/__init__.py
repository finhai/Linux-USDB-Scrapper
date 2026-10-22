"""Public USDB session API."""

from usdb_scrapper.usdb_client.content import decode_html, extract_txt
from usdb_scrapper.usdb_client.details import (
    DetailClient,
    DetailParseError,
    SongDetails,
    parse_song_details,
)
from usdb_scrapper.usdb_client.listing import (
    ListingParseError,
    PagedSearchClient,
    PaginationError,
    parse_listing,
)
from usdb_scrapper.usdb_client.pipeline import (
    PipelineError,
    SearchPipeline,
    SearchStages,
    filter_video_results,
)
from usdb_scrapper.usdb_client.results import merge_song_results
from usdb_scrapper.usdb_client.search import (
    SearchClient,
    SearchQuery,
    SortDirection,
    SortField,
    SortState,
)
from usdb_scrapper.usdb_client.session import (
    AuthenticationError,
    LoginFormError,
    TransportError,
    UsdbError,
    UsdbSession,
)
from usdb_scrapper.usdb_client.session_errors import ContentDecodeError
from usdb_scrapper.usdb_client.txt import TxtClient, TxtRetrievalError

__all__ = [
    "ContentDecodeError",
    "decode_html",
    "extract_txt",
    "TxtClient",
    "TxtRetrievalError",
    "PipelineError",
    "SearchPipeline",
    "SearchStages",
    "filter_video_results",
    "merge_song_results",
    "DetailClient",
    "DetailParseError",
    "SongDetails",
    "parse_song_details",
    "ListingParseError",
    "PagedSearchClient",
    "PaginationError",
    "parse_listing",
    "SearchClient",
    "SearchQuery",
    "SortDirection",
    "SortField",
    "SortState",
    "AuthenticationError",
    "LoginFormError",
    "TransportError",
    "UsdbError",
    "UsdbSession",
]

from usdb_scrapper.usdb_client.session import SessionExpiredError as SessionExpiredError
