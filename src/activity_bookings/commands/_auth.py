"""Helpers for commands that call protected API routes."""

from collections.abc import Iterator
from contextlib import contextmanager

from activity_bookings.api_client import ApiClient
from activity_bookings.config import Settings
from activity_bookings.errors import ActivityBookingsError, ApiError
from activity_bookings.session import require_session

LOGIN_SUGGESTION = "Run 'activity-bookings auth login' to start a new session."


def authorized_client(settings: Settings) -> ApiClient:
    """Check the local session for `settings.api_url` and return a client that sends its token."""
    session = require_session(settings.api_url)
    return ApiClient(settings.api_url, token=session.access_token)


@contextmanager
def login_hint() -> Iterator[None]:
    """Add a login suggestion to a 401 from the API; other errors pass through unchanged.

    The session file is kept: the user decides whether to log in again.
    """
    try:
        yield
    except ApiError as exc:
        if exc.status_code != 401:
            raise
        raise ActivityBookingsError(f"{exc}\n{LOGIN_SUGGESTION}") from exc
