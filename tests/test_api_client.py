import json

import httpx
import pytest
import respx

from activity_bookings.api_client import (
    Activity,
    ApiClient,
    AuthResult,
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
