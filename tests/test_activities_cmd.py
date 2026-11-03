import httpx
import pytest
import respx
from typer.testing import CliRunner, Result

from activity_bookings.cli import app
from activity_bookings.commands.activities_cmd import _format_date, _format_price
from activity_bookings.config import DEFAULT_API_URL, default_config_path

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
