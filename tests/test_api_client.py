import dataclasses
import json

import httpx
import pytest
import respx

from activity_bookings.api_client import (
    Activity,
    ActivityChanges,
    ApiClient,
    AuthResult,
    NewActivity,
    User,
    parse_activity,
    parse_auth_result,
)
from activity_bookings.errors import (
    ApiConnectionError,
    ApiError,
    ApiResponseError,
    FieldError,
)

BASE_URL = "http://api.example.com"
REGISTER_OK = {
    "user": {"id": 2, "username": "Ana", "email": "ana@example.com", "terms": True},
    "accessToken": "tok-123",
}


# --- ApiError text -------------------------------------------------------------------


def test_api_error_without_field_errors() -> None:
    error = ApiError(400, "Failed to register user")
    assert str(error) == "Failed to register user"
    assert error.status_code == 400
    assert error.field_errors == ()


def test_api_error_with_field_errors() -> None:
    error = ApiError(
        400,
        "Validation failed",
        (FieldError("email", "Email must be valid"), FieldError("password", "Too short")),
    )
    assert str(error) == (
        "Validation failed\n  - email: Email must be valid\n  - password: Too short"
    )
    assert error.message == "Validation failed"


# --- parsing -------------------------------------------------------------------------


def test_parse_valid_response() -> None:
    assert parse_auth_result(REGISTER_OK) == AuthResult(
        user=User(id=2, username="Ana", email="ana@example.com"), access_token="tok-123"
    )


def test_parse_text_id() -> None:
    data = {"user": {"id": "user-2", "username": "Ana", "email": "a@b.c"}, "accessToken": "t"}
    assert parse_auth_result(data).user.id == "user-2"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"user": {"id": 2}}, "user.username"),
        ({"user": {"id": 2, "username": "Ana", "email": "a@b.c"}}, "accessToken"),
        ({"accessToken": "tok"}, "'user'"),
        ({"user": "Ana", "accessToken": "tok"}, "'user' is not an object"),
        ({"user": {"username": "Ana", "email": "a@b.c"}, "accessToken": "t"}, "user.id"),
        ({"user": {"id": True, "username": "A", "email": "a@b.c"}, "accessToken": "t"}, "user.id"),
        ({"user": {"id": 2, "username": "Ana", "email": "a@b.c"}, "accessToken": 3}, "accessToken"),
        ([], "not a JSON object"),
    ],
)
def test_parse_incomplete_response(data: object, expected: str) -> None:
    with pytest.raises(ApiResponseError, match="invalid response from the API") as exc:
        parse_auth_result(data)
    assert expected in str(exc.value)


# --- ApiClient.register --------------------------------------------------------------


def register(base_url: str = BASE_URL) -> AuthResult:
    with ApiClient(base_url) as client:
        return client.register("Ana", "ana@example.com", "secret1")


def test_register_sends_body_and_parses_result(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(f"{BASE_URL}/users").respond(201, json=REGISTER_OK)
    result = register()
    assert result.access_token == "tok-123"
    assert result.user == User(id=2, username="Ana", email="ana@example.com")
    assert json.loads(route.calls.last.request.content) == {
        "username": "Ana",
        "email": "ana@example.com",
        "password": "secret1",
        "terms": True,
    }


def test_register_validation_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(
        400,
        json={
            "message": "Validation failed",
            "errors": [
                {"field": "email", "message": "Email must be valid"},
                {"field": "password", "message": "Password must be at least 6 characters"},
            ],
        },
    )
    with pytest.raises(ApiError) as exc:
        register()
    assert exc.value.status_code == 400
    assert exc.value.field_errors == (
        FieldError("email", "Email must be valid"),
        FieldError("password", "Password must be at least 6 characters"),
    )


def test_register_error_without_fields(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(
        400, json={"message": "Failed to register user", "errors": []}
    )
    with pytest.raises(ApiError) as exc:
        register()
    assert str(exc.value) == "Failed to register user"


def test_register_server_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(
        500, json={"message": "Internal server error", "errors": []}
    )
    with pytest.raises(ApiError) as exc:
        register()
    assert exc.value.status_code == 500
    assert str(exc.value) == "API error 500: Internal server error"


@pytest.mark.parametrize("status", [400, 502])
def test_register_non_json_error(respx_mock: respx.MockRouter, status: int) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(status, html="<pre>Bad Request</pre>")
    with pytest.raises(ApiError) as exc:
        register()
    assert str(exc.value) == f"API returned HTTP {status} with an unexpected response"


def test_register_json_error_without_message(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(400, json={"error": "nope"})
    with pytest.raises(ApiError, match="unexpected response"):
        register()


def test_register_connection_refused(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ApiConnectionError, match=f"cannot connect to the API at {BASE_URL}"):
        register()


def test_register_timeout(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(ApiConnectionError, match="did not respond in time"):
        register()


def test_register_other_transport_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").mock(side_effect=httpx.RemoteProtocolError("boom"))
    with pytest.raises(ApiConnectionError, match="request to the API failed: boom"):
        register()


def test_register_success_without_json(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(201, text="created")
    with pytest.raises(ApiResponseError, match="not JSON"):
        register()


def test_register_success_without_token(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(201, json={"user": {"id": 2}})
    with pytest.raises(ApiResponseError):
        register()


# --- ApiClient.login -----------------------------------------------------------------

LOGIN_OK = {
    "user": {"id": 1, "username": "Mark Musk", "email": "m@f.c", "terms": True},
    "accessToken": "tok-123",
}


def login() -> AuthResult:
    with ApiClient(BASE_URL) as client:
        return client.login("m@f.c", "1234aB")


def test_login_sends_body_and_parses_result(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(f"{BASE_URL}/login").respond(200, json=LOGIN_OK)
    result = login()
    assert result == AuthResult(
        user=User(id=1, username="Mark Musk", email="m@f.c"), access_token="tok-123"
    )
    assert json.loads(route.calls.last.request.content) == {
        "email": "m@f.c",
        "password": "1234aB",
    }


def test_login_invalid_credentials(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/login").respond(
        401, json={"message": "Invalid email or password", "errors": []}
    )
    with pytest.raises(ApiError) as exc:
        login()
    assert exc.value.status_code == 401
    assert str(exc.value) == "Invalid email or password"


def test_login_validation_error(respx_mock: respx.MockRouter) -> None:
    message = "Email is required and must be a non-empty string"
    respx_mock.post(f"{BASE_URL}/login").respond(
        400,
        json={"message": "Validation failed", "errors": [{"field": "email", "message": message}]},
    )
    with pytest.raises(ApiError) as exc:
        login()
    assert exc.value.status_code == 400
    assert exc.value.field_errors == (FieldError("email", message),)


def test_login_success_without_token(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/login").respond(200, json={"user": {"id": 1}})
    with pytest.raises(ApiResponseError):
        login()


# --- activities ----------------------------------------------------------------------

ACTIVITIES_URL = f"{BASE_URL}/activities"
ACTIVITY_JSON = {
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
}
CITY_BIKE_TOUR = Activity(
    id="activity-2",
    name="City Bike Tour",
    date="2026-12-20",
    location="City Center",
    price=35.0,
    max_participants=15,
    status="published",
)


def test_parse_activity_valid() -> None:
    assert parse_activity({**ACTIVITY_JSON, "updatedAt": "2026-01-02T00:00:00.000Z"}) == (
        CITY_BIKE_TOUR
    )


def test_parse_activity_extra_fields_and_no_updated_at() -> None:
    assert "updatedAt" not in ACTIVITY_JSON
    assert parse_activity(ACTIVITY_JSON) == CITY_BIKE_TOUR


@pytest.mark.parametrize(("price", "expected"), [(35, 35.0), (35.5, 35.5)])
def test_parse_activity_price(price: object, expected: float) -> None:
    assert parse_activity({**ACTIVITY_JSON, "price": price}).price == expected


def test_parse_activity_without_name() -> None:
    data = {key: value for key, value in ACTIVITY_JSON.items() if key != "name"}
    with pytest.raises(ApiResponseError, match="invalid response from the API") as exc:
        parse_activity(data)
    assert "activity-2" in str(exc.value)
    assert "'name'" in str(exc.value)


def test_parse_activity_boolean_price() -> None:
    with pytest.raises(ApiResponseError, match="'price'"):
        parse_activity({**ACTIVITY_JSON, "price": True})


def test_parse_activity_without_id_uses_position() -> None:
    data = {key: value for key, value in ACTIVITY_JSON.items() if key != "id"}
    with pytest.raises(ApiResponseError, match="activity at position 3 has no valid 'id'"):
        parse_activity(data, 3)


def test_parse_activity_not_an_object() -> None:
    with pytest.raises(ApiResponseError, match="is not an object"):
        parse_activity("activity-2")


def test_list_activities_without_params(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[ACTIVITY_JSON])
    with ApiClient(BASE_URL) as client:
        assert client.list_activities() == [CITY_BIKE_TOUR]
    request = route.calls.last.request
    assert request.url.params.multi_items() == []
    assert "Authorization" not in request.headers


def test_list_activities_search(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[])
    with ApiClient(BASE_URL) as client:
        assert client.list_activities(search="bike") == []
    assert route.calls.last.request.url.params.multi_items() == [("q", "bike")]


def test_list_activities_sort(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[])
    with ApiClient(BASE_URL) as client:
        client.list_activities(sort="price", order="desc")
    assert route.calls.last.request.url.params.multi_items() == [
        ("_sort", "price"),
        ("_order", "desc"),
    ]


def test_list_activities_order_without_sort_is_not_sent(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[])
    with ApiClient(BASE_URL) as client:
        client.list_activities(order="desc")
    assert route.calls.last.request.url.params.multi_items() == []


def test_list_activities_not_a_list(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(200, json={"activities": []})
    with (
        ApiClient(BASE_URL) as client,
        pytest.raises(ApiResponseError, match="expected a list of activities"),
    ):
        client.list_activities()


def test_list_activities_invalid_item(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[ACTIVITY_JSON, {"id": "activity-9"}])
    with (
        ApiClient(BASE_URL) as client,
        pytest.raises(ApiResponseError, match="activity activity-9 has no valid"),
    ):
        client.list_activities()


def test_list_activities_server_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(
        500, json={"message": "Failed to retrieve activities", "errors": []}
    )
    with ApiClient(BASE_URL) as client, pytest.raises(ApiError) as exc:
        client.list_activities()
    assert str(exc.value) == "API error 500: Failed to retrieve activities"
    assert exc.value.status_code == 500


# --- authorization header ------------------------------------------------------------


def test_request_with_token_sends_bearer_header(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[])
    with ApiClient(BASE_URL, token="tok-123") as client:
        client.list_activities()
    assert route.calls.last.request.headers["Authorization"] == "Bearer tok-123"


def test_request_without_token_sends_no_header(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[])
    with ApiClient(BASE_URL) as client:
        client.list_activities()
    assert "Authorization" not in route.calls.last.request.headers


# --- request bodies ------------------------------------------------------------------

NEW_YOGA = NewActivity(
    name="Yoga",
    price=20.0,
    date="2027-01-15",
    location="Park",
    min_participants=2,
    max_participants=10,
)
YOGA_BODY = {
    "name": "Yoga",
    "price": 20,
    "date": "2027-01-15",
    "location": "Park",
    "minParticipants": 2,
    "maxParticipants": 10,
}


def test_new_activity_body_without_duration() -> None:
    assert NEW_YOGA.to_json() == YOGA_BODY


def test_new_activity_body_with_duration() -> None:
    activity = dataclasses.replace(NEW_YOGA, duration=90)
    assert activity.to_json() == {**YOGA_BODY, "duration": 90}


def test_activity_changes_body_only_given_fields() -> None:
    changes = ActivityChanges(price=25.0, max_participants=12)
    assert changes.to_json() == {"price": 25, "maxParticipants": 12}
    assert not changes.is_empty()


def test_activity_changes_all_fields_camel_case() -> None:
    changes = ActivityChanges(
        name="A",
        price=1.5,
        date="d",
        location="L",
        min_participants=1,
        max_participants=2,
        duration=30,
    )
    assert changes.to_json() == {
        "name": "A",
        "price": 1.5,
        "date": "d",
        "location": "L",
        "minParticipants": 1,
        "maxParticipants": 2,
        "duration": 30,
    }


def test_activity_changes_empty() -> None:
    assert ActivityChanges().is_empty()
    assert ActivityChanges().to_json() == {}


def test_bodies_never_contain_status() -> None:
    assert "status" not in NEW_YOGA.to_json()
    assert "status" not in ActivityChanges(name="x").to_json()


# --- create_activity -----------------------------------------------------------------

YOGA_JSON = {
    **ACTIVITY_JSON,
    "id": "activity-5",
    "name": "Yoga",
    "slug": "yoga",
    "date": "2027-01-15",
    "location": "Park",
    "price": 20,
    "minParticipants": 2,
    "maxParticipants": 10,
    "status": "draft",
}
YOGA = Activity(
    id="activity-5",
    name="Yoga",
    date="2027-01-15",
    location="Park",
    price=20.0,
    max_participants=10,
    status="draft",
)


def test_create_activity(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(ACTIVITIES_URL).respond(201, json=YOGA_JSON)
    with ApiClient(BASE_URL, token="tok-123") as client:
        assert client.create_activity(NEW_YOGA) == YOGA
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer tok-123"
    assert json.loads(request.content) == YOGA_BODY


def test_create_activity_validation_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(ACTIVITIES_URL).respond(
        400,
        json={
            "message": "Validation failed",
            "errors": [{"field": "price", "message": "Price must be greater than 0"}],
        },
    )
    with ApiClient(BASE_URL, token="t") as client, pytest.raises(ApiError) as exc:
        client.create_activity(NEW_YOGA)
    assert exc.value.status_code == 400
    assert exc.value.field_errors == (FieldError("price", "Price must be greater than 0"),)


def test_create_activity_unauthorized(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(ACTIVITIES_URL).respond(
        401, json={"message": "Invalid or expired token. Please login again.", "errors": []}
    )
    with ApiClient(BASE_URL, token="t") as client, pytest.raises(ApiError) as exc:
        client.create_activity(NEW_YOGA)
    assert exc.value.status_code == 401
    assert str(exc.value) == "Invalid or expired token. Please login again."


def test_create_activity_incomplete_response(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(ACTIVITIES_URL).respond(201, json={"message": "ok"})
    with (
        ApiClient(BASE_URL, token="t") as client,
        pytest.raises(ApiResponseError, match=r"^invalid response from the API"),
    ):
        client.create_activity(NEW_YOGA)


# --- update_activity -----------------------------------------------------------------


def test_update_activity_partial_body(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.put(f"{ACTIVITIES_URL}/activity-5").respond(
        200, json={**YOGA_JSON, "price": 25}
    )
    with ApiClient(BASE_URL, token="tok-123") as client:
        result = client.update_activity("activity-5", ActivityChanges(price=25.0))
    assert result.price == 25.0
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer tok-123"
    assert json.loads(request.content) == {"price": 25}


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (400, "Validation failed"),
        (403, "You can only update your own activities"),
        (404, "Activity not found"),
    ],
)
def test_update_activity_errors(respx_mock: respx.MockRouter, status: int, message: str) -> None:
    respx_mock.put(f"{ACTIVITIES_URL}/activity-5").respond(
        status, json={"message": message, "errors": []}
    )
    with ApiClient(BASE_URL, token="t") as client, pytest.raises(ApiError) as exc:
        client.update_activity("activity-5", ActivityChanges(price=25.0))
    assert exc.value.status_code == status
    assert str(exc.value) == message


def test_update_activity_encodes_id(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.put(f"{ACTIVITIES_URL}/a%2Fb").respond(200, json=YOGA_JSON)
    with ApiClient(BASE_URL, token="t") as client:
        client.update_activity("a/b", ActivityChanges(name="x"))
    assert route.calls.last.request.url.raw_path == b"/activities/a%2Fb"


# --- delete_activity -----------------------------------------------------------------


def test_delete_activity_no_content(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.delete(f"{ACTIVITIES_URL}/activity-5").respond(204)
    with ApiClient(BASE_URL, token="tok-123") as client:
        client.delete_activity("activity-5")
    assert route.calls.last.request.headers["Authorization"] == "Bearer tok-123"


@pytest.mark.parametrize(
    ("status", "message", "expected"),
    [
        (403, "You can only delete your own activities", "You can only delete your own activities"),
        (404, "Activity not found", "Activity not found"),
        (500, "Failed to delete activity", "API error 500: Failed to delete activity"),
    ],
)
def test_delete_activity_errors(
    respx_mock: respx.MockRouter, status: int, message: str, expected: str
) -> None:
    respx_mock.delete(f"{ACTIVITIES_URL}/activity-5").respond(
        status, json={"message": message, "errors": []}
    )
    with ApiClient(BASE_URL, token="t") as client, pytest.raises(ApiError) as exc:
        client.delete_activity("activity-5")
    assert exc.value.status_code == status
    assert str(exc.value) == expected
