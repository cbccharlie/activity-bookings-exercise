import json
import re
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


# === bookings list ===================================================================


def listed_booking(**overrides: object) -> dict[str, object]:
    """A `GET /bookings` item: a booking of `activity-2` with its activity."""
    activity_overrides = overrides.pop("activity", {})
    assert isinstance(activity_overrides, dict)
    data: dict[str, object] = {
        **booking(participants=2),
        "activity": {
            "name": "City Bike Tour",
            "slug": "city-bike-tour",
            "price": 35,
            "date": "2100-12-20",
            "duration": 180,
            "location": "City Center",
            "status": "published",
            **activity_overrides,
        },
    }
    data.update(overrides)
    return data


def mock_list(respx_mock: respx.MockRouter, *items: object, url: str = BOOKINGS_URL) -> respx.Route:
    return respx_mock.get(url).respond(200, json=list(items))


def list_bookings(runner: CliRunner, *args: str) -> Result:
    return runner.invoke(app, ["bookings", "list", *args])


# --- Subcomando de listado de reservas -----------------------------------------------


def test_bookings_help_lists_create_and_list(runner: CliRunner) -> None:
    result = runner.invoke(app, ["bookings", "--help"])
    assert result.exit_code == 0
    assert re.search(r"^\W*create\s+Book seats", result.stdout, re.MULTILINE)
    assert re.search(r"^\W*list\s+List your bookings", result.stdout, re.MULTILINE)


def test_list_sent_to_configured_api(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    write_config(CUSTOM_API_URL)
    login_as(api_url=CUSTOM_API_URL)
    route = mock_list(respx_mock, url=f"{CUSTOM_API_URL}/bookings")
    result = list_bookings(runner)
    assert result.exit_code == 0, result.output
    assert route.call_count == 1


# --- Tabla de reservas ---------------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_list_several_bookings(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    yoga = listed_booking(
        id="booking-2",
        activityId="activity-5",
        participants=1,
        activity={
            "name": "Yoga",
            "price": 12.5,
            "date": "2100-01-10T09:00:00.000Z",
            "status": "confirmed",
        },
    )
    mock_list(respx_mock, listed_booking(), yoga)
    result = list_bookings(runner)
    assert result.exit_code == 0, result.output
    out = result.stdout
    assert "My bookings" in out
    for fragment in ("booking-1", "City Bike Tour", "activity-2", "2100-12-20", "70.00", "paid"):
        assert fragment in out
    assert "published" in out
    for fragment in ("booking-2", "Yoga", "activity-5", "2100-01-10 09:00 UTC", "12.50"):
        assert fragment in out
    assert "confirmed" in out
    assert out.index("booking-1") < out.index("booking-2")
    assert "2 bookings" in out


@pytest.mark.usefixtures("session_path")
def test_list_one_booking(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_list(respx_mock, listed_booking())
    result = list_bookings(runner)
    assert result.exit_code == 0, result.output
    assert "1 booking" in result.stdout
    assert "1 bookings" not in result.stdout


@pytest.mark.usefixtures("session_path")
def test_list_without_payment_status(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    item = listed_booking()
    del item["paymentStatus"]
    mock_list(respx_mock, item)
    result = list_bookings(runner)
    assert result.exit_code == 0, result.output
    assert "pending" in result.stdout


@pytest.mark.usefixtures("session_path")
def test_list_empty(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_list(respx_mock)
    result = list_bookings(runner)
    assert result.exit_code == 0, result.output
    assert "No bookings found." in result.stdout


# --- Filtro por actividad ------------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_list_filter_by_activity(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = mock_list(respx_mock, listed_booking())
    result = list_bookings(runner, "--activity", "activity-2")
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.url.params["activityId"] == "activity-2"
    assert "activity-2" in result.stdout


@pytest.mark.usefixtures("session_path")
def test_list_without_filter_sends_no_activity_id(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    route = mock_list(respx_mock)
    list_bookings(runner)
    assert "activityId" not in route.calls.last.request.url.params


@pytest.mark.usefixtures("session_path")
def test_list_filter_without_results(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = mock_list(respx_mock)
    result = list_bookings(runner, "--activity", "activity-99")
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.url.params["activityId"] == "activity-99"
    assert "No bookings found." in result.stdout


@pytest.mark.usefixtures("session_path")
def test_list_blank_filter(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = list_bookings(runner, "--activity", " ")
    assert_usage_error(result, respx_mock, "--activity")


# --- Listado con sesión --------------------------------------------------------------


def test_list_authorization_header(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(token="tok-123")
    route = mock_list(respx_mock)
    result = list_bookings(runner)
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.headers["Authorization"] == "Bearer tok-123"
    assert "tok-123" not in result.stdout
    assert "tok-123" not in result.stderr


def test_list_without_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = list_bookings(runner)
    assert_clean_failure(result)
    assert "Error: not logged in" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_list_expired_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(token=EXPIRED_TOKEN)
    result = list_bookings(runner)
    assert_clean_failure(result)
    assert "expired" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_list_session_of_other_api(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(api_url="http://localhost:3000")
    write_config(CUSTOM_API_URL)
    result = list_bookings(runner)
    assert_clean_failure(result)
    for fragment in ("http://localhost:3000", CUSTOM_API_URL, "activity-bookings auth login"):
        assert fragment in result.stderr
    assert respx_mock.calls.call_count == 0


def test_list_token_rejected_by_server(
    runner: CliRunner, respx_mock: respx.MockRouter, session_path: Path
) -> None:
    respx_mock.get(BOOKINGS_URL).respond(
        401, json={"message": "Invalid or expired token. Please login again.", "errors": []}
    )
    result = list_bookings(runner)
    assert_clean_failure(result)
    assert "Error: Invalid or expired token. Please login again." in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert session_path.exists()


# --- Errores del listado -------------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_list_deleted_activity_error(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKINGS_URL).respond(
        500, json={"message": "Failed to retrieve bookings", "errors": []}
    )
    result = list_bookings(runner)
    assert_clean_failure(result)
    assert "Failed to retrieve bookings" in result.stderr
    assert "deleted activity" in result.stderr


@pytest.mark.usefixtures("session_path")
@pytest.mark.parametrize(
    "body",
    [{"id": "booking-1"}, [{"id": "booking-1", "activityId": "activity-2"}]],
    ids=["not-a-list", "incomplete-booking"],
)
def test_list_invalid_response(
    runner: CliRunner, respx_mock: respx.MockRouter, body: object
) -> None:
    respx_mock.get(BOOKINGS_URL).respond(200, json=body)
    result = list_bookings(runner)
    assert_clean_failure(result)
    assert "invalid response from the API" in result.stderr


@pytest.mark.usefixtures("session_path")
def test_list_wrong_server(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKINGS_URL).respond(404, html="<html>Not Found</html>")
    result = list_bookings(runner)
    assert_clean_failure(result)
    assert "404" in result.stderr


@pytest.mark.usefixtures("session_path")
def test_list_api_down(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKINGS_URL).mock(side_effect=httpx.ConnectError("refused"))
    result = list_bookings(runner)
    assert_clean_failure(result)
    assert DEFAULT_API_URL in result.stderr


@pytest.mark.usefixtures("session_path")
def test_list_timeout(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKINGS_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    result = list_bookings(runner)
    assert_clean_failure(result)


# === bookings show ===================================================================

BOOKING_1_URL = f"{BOOKINGS_URL}/booking-1"


def detailed_booking(**overrides: object) -> dict[str, object]:
    """A `GET /bookings/:id` body: `booking-1` with 2 seats in `activity-2`, 120 minutes long."""
    activity_overrides = overrides.pop("activity", {})
    assert isinstance(activity_overrides, dict)
    return listed_booking(
        createdAt="2100-11-03T10:00:00.000Z",
        activity={"duration": 120, **activity_overrides},
        **overrides,
    )


def mock_detail(
    respx_mock: respx.MockRouter, body: object = None, url: str = BOOKING_1_URL
) -> respx.Route:
    return respx_mock.get(url).respond(200, json=detailed_booking() if body is None else body)


def show_booking(runner: CliRunner, *args: str) -> Result:
    return runner.invoke(app, ["bookings", "show", *args])


# --- Subcomando de detalle de reserva ------------------------------------------------


def test_bookings_help_lists_create_list_and_show(runner: CliRunner) -> None:
    result = runner.invoke(app, ["bookings", "--help"])
    assert result.exit_code == 0
    assert re.search(r"^\W*create\s+Book seats", result.stdout, re.MULTILINE)
    assert re.search(r"^\W*list\s+List your bookings", result.stdout, re.MULTILINE)
    assert re.search(r"^\W*show\s+Show one of your bookings", result.stdout, re.MULTILINE)


def test_show_sent_to_configured_api(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    write_config(CUSTOM_API_URL)
    login_as(api_url=CUSTOM_API_URL)
    route = mock_detail(respx_mock, url=f"{CUSTOM_API_URL}/bookings/booking-1")
    result = show_booking(runner, "booking-1")
    assert result.exit_code == 0, result.output
    assert route.call_count == 1


@pytest.mark.usefixtures("session_path")
def test_show_encodes_id(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{BOOKINGS_URL}/a%2Fb").respond(
        404, json={"message": "Booking not found", "errors": []}
    )
    result = show_booking(runner, "a/b")
    assert_clean_failure(result)
    assert route.calls.last.request.url.raw_path == b"/bookings/a%2Fb"


@pytest.mark.usefixtures("session_path")
def test_show_blank_id(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = show_booking(runner, " ")
    assert_usage_error(result, respx_mock, "BOOKING_ID")


@pytest.mark.usefixtures("session_path")
def test_show_missing_id(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = show_booking(runner)
    assert_usage_error(result, respx_mock, "BOOKING_ID")


# --- Ficha de la reserva -------------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_show_complete_booking(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    mock_detail(respx_mock)
    result = show_booking(runner, "booking-1")
    assert result.exit_code == 0, result.output
    out = result.stdout
    for fragment in (
        "booking-1",
        "City Bike Tour",
        "activity-2",
        "2100-12-20",
        "120 min",
        "City Center",
        "35.00",
        "70.00",
        "paid",
        "payment-1",
        "published",
        "2100-11-03 10:00 UTC",
    ):
        assert fragment in out
    for label in ("Seats", "Price", "Total", "Payment ID", "Activity status", "Booked at"):
        assert label in out


@pytest.mark.usefixtures("session_path")
def test_show_without_payment_status(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    body = detailed_booking()
    del body["paymentStatus"]
    del body["paymentId"]
    mock_detail(respx_mock, body)
    result = show_booking(runner, "booking-1")
    assert result.exit_code == 0, result.output
    assert "pending" in result.stdout
    assert "Payment ID" not in result.stdout


# --- Detalle con sesión --------------------------------------------------------------


def test_show_authorization_header(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(token="tok-123")
    route = mock_detail(respx_mock)
    result = show_booking(runner, "booking-1")
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.headers["Authorization"] == "Bearer tok-123"
    assert "tok-123" not in result.stdout
    assert "tok-123" not in result.stderr


def test_show_without_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = show_booking(runner, "booking-1")
    assert_clean_failure(result)
    assert "Error: not logged in" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_show_expired_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(token=EXPIRED_TOKEN)
    result = show_booking(runner, "booking-1")
    assert_clean_failure(result)
    assert "expired" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_show_session_of_other_api(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(api_url="http://localhost:3000")
    write_config(CUSTOM_API_URL)
    result = show_booking(runner, "booking-1")
    assert_clean_failure(result)
    for fragment in ("http://localhost:3000", CUSTOM_API_URL, "activity-bookings auth login"):
        assert fragment in result.stderr
    assert respx_mock.calls.call_count == 0


def test_show_token_rejected_by_server(
    runner: CliRunner, respx_mock: respx.MockRouter, session_path: Path
) -> None:
    respx_mock.get(BOOKING_1_URL).respond(
        401, json={"message": "Invalid or expired token. Please login again.", "errors": []}
    )
    result = show_booking(runner, "booking-1")
    assert_clean_failure(result)
    assert "Error: Invalid or expired token. Please login again." in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert session_path.exists()


# --- Errores del detalle de reserva --------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_show_booking_not_found(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{BOOKINGS_URL}/booking-99").respond(
        404, json={"message": "Booking not found", "errors": []}
    )
    result = show_booking(runner, "booking-99")
    assert_clean_failure(result)
    assert "Error: Booking not found" in result.stderr
    assert "deleted activity" not in result.stderr


@pytest.mark.usefixtures("session_path")
def test_show_deleted_activity_error(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKING_1_URL).respond(
        500, json={"message": "Failed to retrieve booking", "errors": []}
    )
    result = show_booking(runner, "booking-1")
    assert_clean_failure(result)
    assert "Failed to retrieve booking" in result.stderr
    assert "This booking may refer to a deleted activity." in result.stderr


@pytest.mark.usefixtures("session_path")
@pytest.mark.parametrize(
    "body",
    [[], {"id": "booking-1", "activityId": "activity-2"}],
    ids=["not-an-object", "incomplete-booking"],
)
def test_show_invalid_response(
    runner: CliRunner, respx_mock: respx.MockRouter, body: object
) -> None:
    mock_detail(respx_mock, body)
    result = show_booking(runner, "booking-1")
    assert_clean_failure(result)
    assert "invalid response from the API" in result.stderr


@pytest.mark.usefixtures("session_path")
def test_show_wrong_server(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKING_1_URL).respond(404, html="<html>Not Found</html>")
    result = show_booking(runner, "booking-1")
    assert_clean_failure(result)
    assert "404" in result.stderr


@pytest.mark.usefixtures("session_path")
def test_show_api_down(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKING_1_URL).mock(side_effect=httpx.ConnectError("refused"))
    result = show_booking(runner, "booking-1")
    assert_clean_failure(result)
    assert DEFAULT_API_URL in result.stderr


@pytest.mark.usefixtures("session_path")
def test_show_timeout(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKING_1_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    result = show_booking(runner, "booking-1")
    assert_clean_failure(result)
