import json
from pathlib import Path

import httpx
import pytest
import respx
from jwt_helpers import make_jwt
from typer.testing import CliRunner, Result

from activity_bookings.api_client import User
from activity_bookings.cli import app
from activity_bookings.commands.activities_cmd import _format_date, _format_price
from activity_bookings.config import DEFAULT_API_URL, default_config_path
from activity_bookings.session import Session, default_session_path, save_session

ACTIVITIES_URL = f"{DEFAULT_API_URL}/activities"
CUSTOM_API_URL = "http://api.example.com"


def activity(**overrides: object) -> dict[str, object]:
    """An activity as returned by `GET /activities`, with sensible defaults."""
    data: dict[str, object] = {
        "id": "activity-2",
        "name": "City Bike Tour",
        "slug": "city-bike-tour",
        "date": "2026-12-20",
        "duration": 3,
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


def write_config(api_url: str) -> None:
    config = default_config_path()
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f'api_url = "{api_url}"\n', encoding="utf-8")


def run_list(runner: CliRunner, *args: str) -> Result:
    return runner.invoke(app, ["activities", "list", *args])


def sent_params(route: respx.Route) -> list[tuple[str, str]]:
    return route.calls.last.request.url.params.multi_items()


def assert_clean_failure(result: Result) -> None:
    assert result.exit_code == 1
    assert result.stderr.startswith("Error:")
    assert "Traceback" not in result.output


def assert_usage_error(result: Result, respx_mock: respx.MockRouter, *fragments: str) -> None:
    assert result.exit_code == 2
    for fragment in fragments:
        assert fragment in result.stderr
    assert respx_mock.calls.call_count == 0


# --- formatting ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-10-26", "2026-10-26"),
        ("2026-08-25T14:00:00.000Z", "2026-08-25 14:00 UTC"),
        ("2026-08-25T16:00:00+02:00", "2026-08-25 14:00 UTC"),
        ("someday", "someday"),
    ],
)
def test_format_date(value: str, expected: str) -> None:
    assert _format_date(value) == expected


@pytest.mark.parametrize(("value", "expected"), [(35.0, "35.00"), (35.5, "35.50"), (0.0, "0.00")])
def test_format_price(value: float, expected: str) -> None:
    assert _format_price(value) == expected


# --- command group -------------------------------------------------------------------


def test_root_help_lists_activities(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "activities" in result.output


def test_activities_help_lists_list(runner: CliRunner) -> None:
    result = runner.invoke(app, ["activities", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output


def test_request_sent_to_configured_api(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    write_config(CUSTOM_API_URL)
    route = respx_mock.get(f"{CUSTOM_API_URL}/activities").respond(200, json=[])

    result = run_list(runner)

    assert result.exit_code == 0
    assert route.call_count == 1
    assert sent_params(route) == []


def test_invalid_config(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    write_config("ftp://example.com")

    result = run_list(runner)

    assert_clean_failure(result)
    assert "api_url" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_no_authorization_header(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[activity()])

    result = run_list(runner)

    assert result.exit_code == 0
    assert "Authorization" not in route.calls.last.request.headers


# --- table ---------------------------------------------------------------------------


def test_list_several_activities(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    second = activity(id="activity-4", name="Photography Walk", status="draft")
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[activity(maxParticipants=37), second])

    result = run_list(runner)

    assert result.exit_code == 0
    for header in ("ID", "Name", "Date", "Location", "Price", "Capacity", "Status"):
        assert header in result.output
    for value in ("activity-2", "City Bike Tour", "2026-12-20", "City Center", "35.00", "37"):
        assert value in result.output
    assert "published" in result.output
    assert result.output.index("City Bike Tour") < result.output.index("Photography Walk")
    assert "2 activities" in result.output


def test_single_activity_count(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[activity()])

    result = run_list(runner)

    assert result.exit_code == 0
    assert "1 activity" in result.output


def test_all_states_shown_by_default(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    activities = [
        activity(id="a-1", name="Surf", status="draft"),
        activity(id="a-2", name="City Bike Tour", status="published"),
        activity(id="a-3", name="Kayak", status="cancelled"),
    ]
    respx_mock.get(ACTIVITIES_URL).respond(200, json=activities)

    result = run_list(runner)

    assert result.exit_code == 0
    for name in ("Surf", "City Bike Tour", "Kayak"):
        assert name in result.output


def test_date_with_time(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[activity(date="2026-08-25T14:00:00.000Z")])

    result = run_list(runner)

    assert result.exit_code == 0
    assert "2026-08-25 14:00 UTC" in result.output


def test_unparseable_date(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[activity(date="someday")])

    result = run_list(runner)

    assert result.exit_code == 0
    assert "someday" in result.output


def test_extra_fields_without_updated_at(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    data = activity()
    del data["updatedAt"]
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[data])

    result = run_list(runner)

    assert result.exit_code == 0
    assert "City Bike Tour" in result.output


def test_empty_list(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[])

    result = run_list(runner)

    assert result.exit_code == 0
    assert "No activities found." in result.output
    assert "Location" not in result.output


# --- search --------------------------------------------------------------------------


def test_search_sent_to_api(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[])

    result = run_list(runner, "--search", "bike")

    assert result.exit_code == 0
    assert sent_params(route) == [("q", "bike")]


def test_search_without_results(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[])

    result = run_list(runner, "--search", "zzz")

    assert result.exit_code == 0
    assert "No activities found." in result.output


@pytest.mark.parametrize("text", ["", " "])
def test_empty_search(runner: CliRunner, respx_mock: respx.MockRouter, text: str) -> None:
    result = run_list(runner, "--search", text)
    assert_usage_error(result, respx_mock, "--search", "cannot be empty")


# --- sort ----------------------------------------------------------------------------


def test_sort_by_price_desc(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    activities = [
        activity(id="activity-3", name="Cooking Workshop", price=75),
        activity(id="activity-2", name="City Bike Tour", price=35),
    ]
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=activities)

    result = run_list(runner, "--sort", "price", "--order", "desc")

    assert result.exit_code == 0
    assert sent_params(route) == [("_sort", "price"), ("_order", "desc")]
    assert result.output.index("75.00") < result.output.index("35.00")


def test_sort_ascending_by_default(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[])

    result = run_list(runner, "--sort", "date")

    assert result.exit_code == 0
    assert sent_params(route) == [("_sort", "date"), ("_order", "asc")]


def test_search_and_sort(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[])

    result = run_list(runner, "--search", "tour", "--sort", "name")

    assert result.exit_code == 0
    assert sent_params(route) == [("q", "tour"), ("_sort", "name"), ("_order", "asc")]


def test_invalid_sort_field(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = run_list(runner, "--sort", "capacity")
    assert_usage_error(result, respx_mock, "--sort", "capacity")


def test_invalid_sort_order(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = run_list(runner, "--sort", "date", "--order", "up")
    assert_usage_error(result, respx_mock, "--order", "up")


def test_order_without_sort(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = run_list(runner, "--order", "desc")
    assert_usage_error(result, respx_mock, "--order requires --sort")


def test_usage_errors_checked_before_config(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    write_config("ftp://example.com")
    result = run_list(runner, "--order", "desc")
    assert_usage_error(result, respx_mock, "--order requires --sort")


# --- status filter -------------------------------------------------------------------


def test_status_published(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    activities = [
        activity(id="activity-1", name="Surf", status="draft"),
        activity(id="activity-2", name="City Bike Tour", status="published"),
        activity(id="activity-3", name="Cooking Workshop", status="published"),
    ]
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=activities)

    result = run_list(runner, "--status", "published")

    assert result.exit_code == 0
    assert "City Bike Tour" in result.output
    assert "Cooking Workshop" in result.output
    assert "Surf" not in result.output
    assert result.output.index("City Bike Tour") < result.output.index("Cooking Workshop")
    assert "2 activities" in result.output
    assert sent_params(route) == []


def test_status_without_matches(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(
        200, json=[activity(status="draft"), activity(id="a-3", status="published")]
    )

    result = run_list(runner, "--status", "sold-out")

    assert result.exit_code == 0
    assert "No activities found." in result.output


def test_invalid_status(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = run_list(runner, "--status", "open")
    assert_usage_error(result, respx_mock, "--status", "open")


# --- errors --------------------------------------------------------------------------


def test_api_down(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).mock(side_effect=httpx.ConnectError("refused"))

    result = run_list(runner)

    assert_clean_failure(result)
    assert f"Error: cannot connect to the API at {DEFAULT_API_URL}" in result.stderr


def test_timeout(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).mock(side_effect=httpx.ReadTimeout("slow"))

    result = run_list(runner)

    assert_clean_failure(result)
    assert "did not respond in time" in result.stderr


def test_server_error(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(
        500, json={"message": "Failed to retrieve activities", "errors": []}
    )

    result = run_list(runner)

    assert_clean_failure(result)
    assert "Error: API error 500: Failed to retrieve activities" in result.stderr


def test_route_not_found(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(404, html="<pre>Cannot GET /activities</pre>")

    result = run_list(runner)

    assert_clean_failure(result)
    assert "Error: API returned HTTP 404 with an unexpected response" in result.stderr


def test_response_not_a_list(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(200, json={"activities": []})

    result = run_list(runner)

    assert_clean_failure(result)
    assert result.stderr.startswith("Error: invalid response from the API")


def test_activity_without_name(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    data = activity()
    del data["name"]
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[data])

    result = run_list(runner)

    assert_clean_failure(result)
    assert result.stderr.startswith("Error: invalid response from the API")
    assert "name" in result.stderr


# --- managing activities -------------------------------------------------------------

TOKEN = make_jwt(4102444800)  # exp in 2100
EXPIRED_TOKEN = make_jwt(946684800)  # exp in 2000
YOGA_RESPONSE = activity(
    id="activity-5",
    name="Yoga",
    slug="yoga",
    date="2027-01-15",
    duration=60,
    location="Park",
    price=20,
    minParticipants=2,
    maxParticipants=10,
    status="draft",
)
CREATE_ARGS = [
    "activities",
    "create",
    "--name",
    "Yoga",
    "--price",
    "20",
    "--date",
    "2027-01-15",
    "--location",
    "Park",
    "--min-participants",
    "2",
    "--max-participants",
    "10",
]
YOGA_BODY = {
    "name": "Yoga",
    "price": 20,
    "date": "2027-01-15",
    "location": "Park",
    "minParticipants": 2,
    "maxParticipants": 10,
}
ACTIVITY_5_URL = f"{ACTIVITIES_URL}/activity-5"


def login_as(token: str = TOKEN, api_url: str = DEFAULT_API_URL) -> Path:
    user = User(id="user-1", username="Ana", email="ana@example.com")
    return save_session(Session(api_url=api_url, access_token=token, user=user))


@pytest.fixture
def session_path() -> Path:
    """A valid session for the default API with a JWT that expires in 2100."""
    return login_as()


def create_args(**replace: str) -> list[str]:
    """CREATE_ARGS with some option values replaced, e.g. `price="12.5"`."""
    args = list(CREATE_ARGS)
    for key, value in replace.items():
        args[args.index(f"--{key.replace('_', '-')}") + 1] = value
    return args


def sent_json(route: respx.Route) -> object:
    return json.loads(route.calls.last.request.content)


def assert_no_token(result: Result, token: str = TOKEN) -> None:
    assert token not in result.stdout
    assert token not in result.stderr


def test_group_help_lists_all_subcommands(runner: CliRunner) -> None:
    result = runner.invoke(app, ["activities", "--help"])
    assert result.exit_code == 0
    for command in ("list", "create", "update", "delete"):
        assert command in result.stdout


# --- create --------------------------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_create_sends_body_and_header(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(ACTIVITIES_URL).respond(201, json=YOGA_RESPONSE)
    result = runner.invoke(app, CREATE_ARGS)
    assert result.exit_code == 0, result.output
    assert route.call_count == 1
    assert route.calls.last.request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert sent_json(route) == YOGA_BODY


@pytest.mark.usefixtures("session_path")
def test_create_with_duration(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(ACTIVITIES_URL).respond(201, json=YOGA_RESPONSE)
    result = runner.invoke(app, [*CREATE_ARGS, "--duration", "90"])
    assert result.exit_code == 0
    assert sent_json(route) == {**YOGA_BODY, "duration": 90}


@pytest.mark.usefixtures("session_path")
def test_create_decimal_price(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(ACTIVITIES_URL).respond(201, json=YOGA_RESPONSE)
    result = runner.invoke(app, create_args(price="12.5"))
    assert result.exit_code == 0
    body = sent_json(route)
    assert isinstance(body, dict)
    assert body["price"] == 12.5


@pytest.mark.usefixtures("session_path")
def test_create_shows_activity(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(ACTIVITIES_URL).respond(
        201, json={**YOGA_RESPONSE, "createdAt": "2026-11-03T10:00:00.000Z"}
    )
    result = runner.invoke(app, CREATE_ARGS)
    assert result.exit_code == 0
    assert "Activity activity-5 created." in result.stdout
    for fragment in ("Yoga", "2027-01-15", "Park", "20.00", "10", "draft"):
        assert fragment in result.stdout
    assert_no_token(result)


@pytest.mark.usefixtures("session_path")
def test_create_missing_required_option(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    args = [arg for arg in CREATE_ARGS if arg not in ("--location", "Park")]
    result = runner.invoke(app, args)
    assert_usage_error(result, respx_mock, "--location")


@pytest.mark.usefixtures("session_path")
def test_create_invalid_number(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = runner.invoke(app, create_args(max_participants="diez"))
    assert_usage_error(result, respx_mock, "--max-participants")


@pytest.mark.usefixtures("session_path")
def test_create_validation_errors(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(ACTIVITIES_URL).respond(
        400,
        json={
            "message": "Validation failed",
            "errors": [
                {"field": "date", "message": "Date must be in the future"},
                {"field": "price", "message": "Price must be greater than 0"},
            ],
        },
    )
    result = runner.invoke(app, create_args(date="2020-01-01", price="0"))
    assert_clean_failure(result)
    assert "Error: Validation failed" in result.stderr
    assert "date: Date must be in the future" in result.stderr
    assert "price: Price must be greater than 0" in result.stderr


@pytest.mark.usefixtures("session_path")
def test_create_api_down(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(ACTIVITIES_URL).mock(side_effect=httpx.ConnectError("refused"))
    result = runner.invoke(app, CREATE_ARGS)
    assert_clean_failure(result)
    assert "Error: cannot connect to the API at http://localhost:3000" in result.stderr


@pytest.mark.usefixtures("session_path")
def test_create_incomplete_response(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(ACTIVITIES_URL).respond(201, json={"message": "ok"})
    result = runner.invoke(app, CREATE_ARGS)
    assert_clean_failure(result)
    assert result.stderr.startswith("Error: invalid response from the API")


def test_create_without_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = runner.invoke(app, CREATE_ARGS)
    assert_clean_failure(result)
    assert "Error: not logged in" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_create_session_of_other_api(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(api_url=DEFAULT_API_URL)
    write_config(CUSTOM_API_URL)
    result = runner.invoke(app, CREATE_ARGS)
    assert_clean_failure(result)
    for fragment in (DEFAULT_API_URL, CUSTOM_API_URL, "activity-bookings auth login"):
        assert fragment in result.stderr
    assert respx_mock.calls.call_count == 0


def test_create_expired_token(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(token=EXPIRED_TOKEN)
    result = runner.invoke(app, CREATE_ARGS)
    assert_clean_failure(result)
    assert "expired" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_create_token_rejected_by_server(
    runner: CliRunner, respx_mock: respx.MockRouter, session_path: Path
) -> None:
    respx_mock.post(ACTIVITIES_URL).respond(
        401, json={"message": "Invalid or expired token. Please login again.", "errors": []}
    )
    result = runner.invoke(app, CREATE_ARGS)
    assert_clean_failure(result)
    assert "Error: Invalid or expired token. Please login again." in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert session_path.exists()


# --- update --------------------------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_update_sends_only_given_fields(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.put(ACTIVITY_5_URL).respond(200, json=YOGA_RESPONSE)
    result = runner.invoke(
        app, ["activities", "update", "activity-5", "--price", "25", "--max-participants", "12"]
    )
    assert result.exit_code == 0, result.output
    assert route.call_count == 1
    assert route.calls.last.request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert sent_json(route) == {"price": 25, "maxParticipants": 12}


@pytest.mark.usefixtures("session_path")
def test_update_shows_activity(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.put(ACTIVITY_5_URL).respond(
        200, json={**YOGA_RESPONSE, "name": "Yoga al aire libre", "price": 25}
    )
    result = runner.invoke(
        app,
        ["activities", "update", "activity-5", "--name", "Yoga al aire libre", "--price", "25"],
    )
    assert result.exit_code == 0
    assert "Activity activity-5 updated." in result.stdout
    assert "Yoga al aire libre" in result.stdout
    assert "25.00" in result.stdout


@pytest.mark.usefixtures("session_path")
def test_update_without_fields(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = runner.invoke(app, ["activities", "update", "activity-5"])
    assert_usage_error(result, respx_mock, "at least one field to update is required")


def test_update_without_id(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = runner.invoke(app, ["activities", "update", "--price", "25"])
    assert_usage_error(result, respx_mock, "ACTIVITY_ID")


@pytest.mark.usefixtures("session_path")
def test_update_validation_error(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.put(ACTIVITY_5_URL).respond(
        400,
        json={
            "message": "Validation failed",
            "errors": [
                {
                    "field": "minParticipants",
                    "message": "Min participants cannot exceed max participants",
                }
            ],
        },
    )
    result = runner.invoke(app, ["activities", "update", "activity-5", "--min-participants", "20"])
    assert_clean_failure(result)
    assert "Error: Validation failed" in result.stderr
    assert "minParticipants: Min participants cannot exceed max participants" in result.stderr


@pytest.mark.usefixtures("session_path")
def test_update_activity_of_other_user(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.put(f"{ACTIVITIES_URL}/activity-2").respond(
        403, json={"message": "You can only update your own activities", "errors": []}
    )
    result = runner.invoke(app, ["activities", "update", "activity-2", "--price", "40"])
    assert_clean_failure(result)
    assert "Error: You can only update your own activities" in result.stderr


@pytest.mark.usefixtures("session_path")
def test_update_timeout(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.put(ACTIVITY_5_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    result = runner.invoke(app, ["activities", "update", "activity-5", "--price", "25"])
    assert_clean_failure(result)
    assert "did not respond in time" in result.stderr


def test_update_corrupt_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    path = default_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json", encoding="utf-8")
    result = runner.invoke(app, ["activities", "update", "activity-5", "--price", "25"])
    assert_clean_failure(result)
    assert str(path) in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_update_expired_token(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    login_as(token=EXPIRED_TOKEN)
    result = runner.invoke(app, ["activities", "update", "activity-5", "--price", "25"])
    assert_clean_failure(result)
    assert "expired" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_update_token_without_readable_expiry(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    login_as(token="tok-123")
    route = respx_mock.put(ACTIVITY_5_URL).respond(200, json=YOGA_RESPONSE)
    result = runner.invoke(app, ["activities", "update", "activity-5", "--price", "25"])
    assert result.exit_code == 0
    assert route.call_count == 1
    assert route.calls.last.request.headers["Authorization"] == "Bearer tok-123"
    assert_no_token(result, "tok-123")


# --- delete --------------------------------------------------------------------------


def delete(runner: CliRunner, *args: str, input: str | None = None) -> Result:
    return runner.invoke(app, ["activities", "delete", *args], input=input)


@pytest.mark.usefixtures("session_path")
def test_delete_confirmed(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.delete(ACTIVITY_5_URL).respond(204)
    result = delete(runner, "activity-5", input="y\n")
    assert result.exit_code == 0
    assert "Delete activity activity-5? [y/N]" in result.stdout
    assert "Activity activity-5 deleted." in result.stdout
    assert route.call_count == 1
    assert route.calls.last.request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert_no_token(result)


@pytest.mark.parametrize("flag", ["--yes", "-y"])
@pytest.mark.usefixtures("session_path")
def test_delete_without_prompt(runner: CliRunner, respx_mock: respx.MockRouter, flag: str) -> None:
    respx_mock.delete(ACTIVITY_5_URL).respond(204)
    result = delete(runner, "activity-5", flag)
    assert result.exit_code == 0
    assert "Delete activity" not in result.stdout
    assert "Activity activity-5 deleted." in result.stdout


def test_delete_yes_sends_plain_token_without_showing_it(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    login_as(token="tok-123")
    route = respx_mock.delete(ACTIVITY_5_URL).respond(204)
    result = delete(runner, "activity-5", "--yes")
    assert result.exit_code == 0
    assert route.calls.last.request.headers["Authorization"] == "Bearer tok-123"
    assert_no_token(result, "tok-123")


@pytest.mark.parametrize("answer", ["n\n", "\n"])
@pytest.mark.usefixtures("session_path")
def test_delete_cancelled(runner: CliRunner, respx_mock: respx.MockRouter, answer: str) -> None:
    result = delete(runner, "activity-5", input=answer)
    assert result.exit_code == 0
    assert "Deletion cancelled." in result.stdout
    assert respx_mock.calls.call_count == 0


def test_delete_without_session_does_not_prompt(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    result = delete(runner, "activity-5")
    assert_clean_failure(result)
    assert "Delete activity" not in result.stdout
    assert "Error: not logged in" in result.stderr
    assert respx_mock.calls.call_count == 0


@pytest.mark.parametrize(
    ("activity_id", "status", "message", "expected"),
    [
        (
            "activity-2",
            403,
            "You can only delete your own activities",
            "Error: You can only delete your own activities",
        ),
        ("activity-99", 404, "Activity not found", "Error: Activity not found"),
        (
            "activity-5",
            500,
            "Failed to delete activity",
            "Error: API error 500: Failed to delete activity",
        ),
    ],
)
@pytest.mark.usefixtures("session_path")
def test_delete_errors(
    runner: CliRunner,
    respx_mock: respx.MockRouter,
    activity_id: str,
    status: int,
    message: str,
    expected: str,
) -> None:
    respx_mock.delete(f"{ACTIVITIES_URL}/{activity_id}").respond(
        status, json={"message": message, "errors": []}
    )
    result = delete(runner, activity_id, "--yes")
    assert_clean_failure(result)
    assert expected in result.stderr
