import pytest
import respx
from jwt_helpers import make_jwt

from activity_bookings.api_client import User
from activity_bookings.commands._auth import authorized_client, login_hint
from activity_bookings.config import Settings
from activity_bookings.errors import ActivityBookingsError, ApiError, SessionError
from activity_bookings.session import Session, save_session

API_URL = "http://api.example.com"
TOKEN = make_jwt(4102444800)


def test_authorized_client_sends_session_token(respx_mock: respx.MockRouter) -> None:
    save_session(Session(API_URL, TOKEN, User(id=2, username="Ana", email="ana@example.com")))
    route = respx_mock.get(f"{API_URL}/activities").respond(200, json=[])
    with authorized_client(Settings(api_url=API_URL, source=None)) as client:
        client.list_activities()
    assert route.calls.last.request.headers["Authorization"] == f"Bearer {TOKEN}"


def test_authorized_client_without_session() -> None:
    with pytest.raises(SessionError, match="not logged in"):
        authorized_client(Settings(api_url=API_URL, source=None))


def test_login_hint_adds_suggestion_to_401() -> None:
    with pytest.raises(ActivityBookingsError) as exc, login_hint():
        raise ApiError(401, "Invalid or expired token. Please login again.")
    assert str(exc.value) == (
        "Invalid or expired token. Please login again.\n"
        "Run 'activity-bookings auth login' to start a new session."
    )


@pytest.mark.parametrize("status", [400, 403, 404, 500])
def test_login_hint_leaves_other_errors_unchanged(status: int) -> None:
    error = ApiError(status, "boom")
    with pytest.raises(ApiError) as exc, login_hint():
        raise error
    assert exc.value is error


def test_login_hint_without_error() -> None:
    with login_hint():
        pass
