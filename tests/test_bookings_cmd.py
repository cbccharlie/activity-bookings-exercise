import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx
from jwt_helpers import make_jwt
from typer.testing import CliRunner, Result

from activity_bookings.api_client import User
from activity_bookings.cli import app
from activity_bookings.commands import bookings_cmd
from activity_bookings.config import DEFAULT_API_URL, default_config_path
from activity_bookings.session import Session, save_session

CUSTOM_API_URL = "http://api.example.com"
TOKEN = make_jwt(4102444800)  # exp in 2100
EXPIRED_TOKEN = make_jwt(946684800)  # exp in 2000
ACTIVITY_2_URL = f"{DEFAULT_API_URL}/activities/activity-2"
BOOKINGS_URL = f"{DEFAULT_API_URL}/bookings"


def activity(**overrides: object) -> dict[str, object]:
    """An activity as returned by `GET /activities/:id`, bookable by default."""
    data: dict[str, object] = {
        "id": "activity-2",
        "name": "City Bike Tour",
        "slug": "city-bike-tour",
        "date": "2100-12-20",
        "duration": 180,
        "location": "City Center",
        "price": 35,
        "minParticipants": 4,
        "maxParticipants": 15,
        "status": "published",
        "userId": "user-1",
        "createdAt": "2026-01-01T00:00:00.000Z",
        "updatedAt": "2026-01-02T00:00:00.000Z",
    }
    data.update(overrides)
    return data


def booking(participants: int = 1) -> dict[str, object]:
    return {
        "id": "booking-1",
        "activityId": "activity-2",
        "userId": "user-1",
        "participants": participants,
        "createdAt": "2026-11-03T10:00:00.000Z",
        "paymentId": "payment-1",
        "paymentStatus": "paid",
    }


def login_as(token: str = TOKEN, api_url: str = DEFAULT_API_URL) -> Path:
    user = User(id="user-1", username="Ana", email="ana@example.com")
    return save_session(Session(api_url=api_url, access_token=token, user=user))


@pytest.fixture
def session_path() -> Path:
    """A valid session for the default API with a JWT that expires in 2100."""
    return login_as()


def write_config(api_url: str) -> None:
    config = default_config_path()
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f'api_url = "{api_url}"\n', encoding="utf-8")


def mock_activity(respx_mock: respx.MockRouter, **overrides: object) -> respx.Route:
    activity_id = overrides.get("id", "activity-2")
    url = f"{DEFAULT_API_URL}/activities/{activity_id}"
    return respx_mock.get(url).respond(200, json=activity(**overrides))


def mock_booking(respx_mock: respx.MockRouter, participants: int = 1) -> respx.Route:
    return respx_mock.post(BOOKINGS_URL).respond(201, json=booking(participants))


def book(runner: CliRunner, *args: str, input: str | None = None) -> Result:
    return runner.invoke(app, ["bookings", "create", *args], input=input)


def sent_json(route: respx.Route) -> object:
    return json.loads(route.calls.last.request.content)


def assert_clean_failure(result: Result) -> None:
    assert result.exit_code == 1
    assert result.stderr.startswith("Error:")
    assert "Traceback" not in result.output


def assert_usage_error(result: Result, respx_mock: respx.MockRouter, *fragments: str) -> None:
    assert result.exit_code == 2
    for fragment in fragments:
        assert fragment in result.stderr
    assert respx_mock.calls.call_count == 0


# --- Subcomando de reserva -----------------------------------------------------------


def test_root_help_lists_bookings(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "bookings" in result.stdout


def test_bookings_help_lists_create(runner: CliRunner) -> None:
    result = runner.invoke(app, ["bookings", "--help"])
    assert result.exit_code == 0
    assert "create" in result.stdout


@pytest.mark.usefixtures("session_path")
def test_default_participants(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_activity(respx_mock)
    route = mock_booking(respx_mock)
    result = book(runner, "activity-2", "--yes")
    assert result.exit_code == 0, result.output
    assert sent_json(route) == {"activityId": "activity-2", "participants": 1}


@pytest.mark.usefixtures("session_path")
def test_several_participants_as_integer(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_activity(respx_mock)
    route = mock_booking(respx_mock, participants=2)
    result = book(runner, "activity-2", "-p", "2", "-y")
    assert result.exit_code == 0, result.output
    body = sent_json(route)
    assert body == {"activityId": "activity-2", "participants": 2}
    assert isinstance(body, dict)
    assert type(body["participants"]) is int


def test_request_sent_to_configured_api(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    write_config(CUSTOM_API_URL)
    login_as(api_url=CUSTOM_API_URL)
    get = respx_mock.get(f"{CUSTOM_API_URL}/activities/activity-2").respond(200, json=activity())
    post = respx_mock.post(f"{CUSTOM_API_URL}/bookings").respond(201, json=booking())
    result = book(runner, "activity-2", "--yes")
    assert result.exit_code == 0, result.output
    assert get.call_count == 1
    assert post.call_count == 1


# --- Resultado de la reserva ---------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_booking_card(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_activity(respx_mock)
    mock_booking(respx_mock, participants=2)
    result = book(runner, "activity-2", "-p", "2", "--yes")
    assert result.exit_code == 0
    assert "Booking booking-1 created." in result.stdout
    for fragment in ("City Bike Tour", "activity-2", "2100-12-20", "70.00", "paid"):
        assert fragment in result.stdout


@pytest.mark.usefixtures("session_path")
def test_incomplete_booking_response(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_activity(respx_mock)
    respx_mock.post(BOOKINGS_URL).respond(201, json={"activityId": "activity-2"})
    result = book(runner, "activity-2", "--yes")
    assert_clean_failure(result)
    assert result.stderr.startswith("Error: invalid response from the API")


# --- Validación de la entrada --------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_missing_id(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = book(runner)
    assert_usage_error(result, respx_mock, "ACTIVITY_ID")


@pytest.mark.usefixtures("session_path")
def test_blank_id(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = book(runner, " ", "--yes")
    assert_usage_error(result, respx_mock, "ACTIVITY_ID cannot be empty")


@pytest.mark.usefixtures("session_path")
@pytest.mark.parametrize("value", ["0", "1.5"])
def test_invalid_participants(runner: CliRunner, respx_mock: respx.MockRouter, value: str) -> None:
    result = book(runner, "activity-2", "--participants", value, "--yes")
    assert_usage_error(result, respx_mock, "--participants")


# --- Reserva con sesión --------------------------------------------------------------


def test_authorization_header(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(token="tok-123")
    mock_activity(respx_mock)
    route = mock_booking(respx_mock)
    result = book(runner, "activity-2", "--yes")
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.headers["Authorization"] == "Bearer tok-123"
    assert "tok-123" not in result.stdout
    assert "tok-123" not in result.stderr


def test_without_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = book(runner, "activity-2", input="y\n")
    assert_clean_failure(result)
    assert "Book " not in result.output
    assert "Error: not logged in" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_expired_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(token=EXPIRED_TOKEN)
    result = book(runner, "activity-2", "--yes")
    assert_clean_failure(result)
    assert "expired" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_token_rejected_by_server(
    runner: CliRunner, respx_mock: respx.MockRouter, session_path: Path
) -> None:
    mock_activity(respx_mock)
    respx_mock.post(BOOKINGS_URL).respond(
        401, json={"message": "Invalid or expired token. Please login again.", "errors": []}
    )
    result = book(runner, "activity-2", "--yes")
    assert_clean_failure(result)
    assert "Error: Invalid or expired token. Please login again." in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert session_path.exists()


# --- Solo actividades abiertas -------------------------------------------------------


@pytest.mark.usefixtures("session_path")
@pytest.mark.parametrize(
    ("overrides", "fragments"),
    [
        (
            {"id": "activity-4", "status": "draft", "date": "2100-03-01T09:00:00.000Z"},
            ("activity-4", "not open for booking", "draft"),
        ),
        ({"status": "cancelled"}, ("activity-2", "not open for booking", "cancelled")),
        (
            {"id": "activity-3", "date": "2000-08-25T14:00:00.000Z"},
            ("activity-3", "already took place"),
        ),
        ({"date": "pronto"}, ("activity-2",)),
    ],
)
def test_activity_not_bookable(
    runner: CliRunner,
    respx_mock: respx.MockRouter,
    overrides: dict[str, object],
    fragments: tuple[str, ...],
) -> None:
    mock_activity(respx_mock, **overrides)
    post = mock_booking(respx_mock)
    activity_id = str(overrides.get("id", "activity-2"))
    result = book(runner, activity_id, "--yes")
    assert_clean_failure(result)
    for fragment in fragments:
        assert fragment in result.stderr
    assert post.call_count == 0


@pytest.mark.usefixtures("session_path")
def test_activity_today_without_time(
    runner: CliRunner, respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bookings_cmd, "_now", lambda: datetime(2026, 12, 20, 23, 0, tzinfo=UTC))
    mock_activity(respx_mock, date="2026-12-20")
    post = mock_booking(respx_mock)
    result = book(runner, "activity-2", "--yes")
    assert result.exit_code == 0, result.output
    assert post.call_count == 1


@pytest.mark.usefixtures("session_path")
def test_activity_not_found(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{DEFAULT_API_URL}/activities/activity-99").respond(
        404, json={"message": "Activity not found", "errors": []}
    )
    post = mock_booking(respx_mock)
    result = book(runner, "activity-99", "--yes")
    assert_clean_failure(result)
    assert "Error: Activity not found" in result.stderr
    assert post.call_count == 0


# --- Confirmación del cobro ----------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_confirmation_accepted(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_activity(respx_mock)
    post = mock_booking(respx_mock, participants=2)
    result = book(runner, "activity-2", "-p", "2", input="y\n")
    assert result.exit_code == 0, result.output
    question = result.stdout.splitlines()[0]
    for fragment in ("Book 2 seat(s)", "City Bike Tour", "activity-2", "70.00"):
        assert fragment in question
    assert post.call_count == 1


@pytest.mark.usefixtures("session_path")
def test_confirmation_rejected(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_activity(respx_mock)
    post = mock_booking(respx_mock)
    result = book(runner, "activity-2", input="n\n")
    assert result.exit_code == 0
    assert "Booking cancelled." in result.stdout
    assert post.call_count == 0


@pytest.mark.usefixtures("session_path")
def test_yes_skips_confirmation(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_activity(respx_mock)
    post = mock_booking(respx_mock)
    result = book(runner, "activity-2", "--yes")
    assert result.exit_code == 0
    assert "?" not in result.stdout
    assert post.call_count == 1


# --- Errores de la reserva -----------------------------------------------------------


@pytest.mark.usefixtures("session_path")
@pytest.mark.parametrize(
    ("status", "body", "fragments"),
    [
        (
            400,
            {"message": "Capacity exceeded. Available: 13, Requested: 20", "errors": []},
            ("Error: Capacity exceeded. Available: 13, Requested: 20",),
        ),
        (
            400,
            {
                "message": "Validation failed",
                "errors": [
                    {
                        "field": "participants",
                        "message": "Participants is required and must be a positive number "
                        "(at least 1)",
                    }
                ],
            },
            ("Error: Validation failed", "participants", "at least 1"),
        ),
        (
            402,
            {"message": "Payment could not be processed", "errors": []},
            ("Error: Payment could not be processed",),
        ),
        (404, {"message": "Activity not found", "errors": []}, ("Error: Activity not found",)),
        (500, {"message": "Internal error", "errors": []}, ("Error:", "500")),
    ],
)
def test_booking_api_errors(
    runner: CliRunner,
    respx_mock: respx.MockRouter,
    status: int,
    body: dict[str, object],
    fragments: tuple[str, ...],
) -> None:
    mock_activity(respx_mock)
    respx_mock.post(BOOKINGS_URL).respond(status, json=body)
    result = book(runner, "activity-2", "-p", "20", "--yes")
    assert_clean_failure(result)
    for fragment in fragments:
        assert fragment in result.stderr


@pytest.mark.usefixtures("session_path")
def test_api_down(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITY_2_URL).mock(side_effect=httpx.ConnectError("refused"))
    result = book(runner, "activity-2", "--yes")
    assert_clean_failure(result)
    assert DEFAULT_API_URL in result.stderr


@pytest.mark.usefixtures("session_path")
def test_booking_timeout(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_activity(respx_mock)
    respx_mock.post(BOOKINGS_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    result = book(runner, "activity-2", "--yes")
    assert_clean_failure(result)
