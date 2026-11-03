import dataclasses
import json

import httpx
import pytest
import respx

from activity_bookings.api_client import (
    Activity,
    ActivityChanges,
    ActivityDetail,
    ApiClient,
    AuthResult,
    Booking,
    BookingActivity,
    BookingSummary,
    NewActivity,
    User,
    parse_activity,
    parse_activity_detail,
    parse_auth_result,
    parse_booking,
    parse_booking_summary,
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


# --- activity detail -----------------------------------------------------------------

DETAIL_JSON = {
    **ACTIVITY_JSON,
    "duration": 120,
    "minParticipants": 3,
    "createdAt": "2026-01-16T10:00:00.000Z",
}
CITY_BIKE_TOUR_DETAIL = ActivityDetail(
    activity=CITY_BIKE_TOUR,
    slug="city-bike-tour",
    duration=120,
    min_participants=3,
    user_id="user-1",
    created_at="2026-01-16T10:00:00.000Z",
    updated_at=None,
)


def test_parse_activity_detail_complete() -> None:
    data = {**DETAIL_JSON, "updatedAt": "2026-02-01T08:30:00.000Z"}
    assert parse_activity_detail(data) == dataclasses.replace(
        CITY_BIKE_TOUR_DETAIL, updated_at="2026-02-01T08:30:00.000Z"
    )


def test_parse_activity_detail_without_updated_at() -> None:
    assert parse_activity_detail(DETAIL_JSON) == CITY_BIKE_TOUR_DETAIL


def test_parse_activity_detail_null_updated_at() -> None:
    assert parse_activity_detail({**DETAIL_JSON, "updatedAt": None}) == CITY_BIKE_TOUR_DETAIL


def test_parse_activity_detail_whole_float_duration() -> None:
    detail = parse_activity_detail({**DETAIL_JSON, "duration": 120.0})
    assert detail.duration == 120
    assert isinstance(detail.duration, int)


@pytest.mark.parametrize("duration", [None, True, 1.5, "120"])
def test_parse_activity_detail_invalid_duration(duration: object) -> None:
    data = {**DETAIL_JSON, "duration": duration}
    with pytest.raises(ApiResponseError, match="activity activity-2 has no valid 'duration'"):
        parse_activity_detail(data)


def test_parse_activity_detail_missing_duration() -> None:
    data = {key: value for key, value in DETAIL_JSON.items() if key != "duration"}
    with pytest.raises(ApiResponseError, match="'duration'"):
        parse_activity_detail(data)


def test_parse_activity_detail_user_id_not_text() -> None:
    with pytest.raises(ApiResponseError, match="'userId'"):
        parse_activity_detail({**DETAIL_JSON, "userId": 1})


def test_parse_activity_detail_updated_at_not_text() -> None:
    with pytest.raises(ApiResponseError, match="'updatedAt'"):
        parse_activity_detail({**DETAIL_JSON, "updatedAt": 5})


@pytest.mark.parametrize("data", [[], "x", None])
def test_parse_activity_detail_not_an_object(data: object) -> None:
    with pytest.raises(ApiResponseError, match=r"^invalid response from the API: expected an"):
        parse_activity_detail(data)


def test_get_activity(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{ACTIVITIES_URL}/activity-2").respond(200, json=DETAIL_JSON)
    with ApiClient(BASE_URL) as client:
        assert client.get_activity("activity-2") == CITY_BIKE_TOUR_DETAIL
    assert route.call_count == 1
    assert "Authorization" not in route.calls.last.request.headers


def test_get_activity_encodes_id(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{ACTIVITIES_URL}/a%2Fb%20c").respond(
        404, json={"message": "Activity not found", "errors": []}
    )
    with ApiClient(BASE_URL) as client, pytest.raises(ApiError):
        client.get_activity("a/b c")
    assert route.calls.last.request.url.raw_path == b"/activities/a%2Fb%20c"


@pytest.mark.parametrize(
    ("status", "message", "expected"),
    [
        (404, "Activity not found", "Activity not found"),
        (500, "Failed to retrieve activity", "API error 500: Failed to retrieve activity"),
    ],
)
def test_get_activity_errors(
    respx_mock: respx.MockRouter, status: int, message: str, expected: str
) -> None:
    respx_mock.get(f"{ACTIVITIES_URL}/activity-2").respond(
        status, json={"message": message, "errors": []}
    )
    with ApiClient(BASE_URL) as client, pytest.raises(ApiError) as exc:
        client.get_activity("activity-2")
    assert exc.value.status_code == status
    assert str(exc.value) == expected


# --- bookings ------------------------------------------------------------------------

BOOKINGS_URL = f"{BASE_URL}/bookings"
BOOKING_JSON: dict[str, object] = {
    "id": "booking-1",
    "activityId": "activity-2",
    "userId": "user-1",
    "participants": 2,
    "createdAt": "2026-11-03T10:00:00.000Z",
    "paymentId": "payment-1",
    "paymentStatus": "paid",
}
BOOKING = Booking(
    id="booking-1",
    activity_id="activity-2",
    user_id="user-1",
    participants=2,
    created_at="2026-11-03T10:00:00.000Z",
    payment_status="paid",
)


def test_parse_booking() -> None:
    assert parse_booking(BOOKING_JSON) == BOOKING


def test_parse_booking_without_payment_status() -> None:
    data = {key: value for key, value in BOOKING_JSON.items() if key != "paymentStatus"}
    assert parse_booking(data).payment_status == "pending"


def test_parse_booking_whole_float_participants() -> None:
    booking = parse_booking({**BOOKING_JSON, "participants": 2.0})
    assert booking.participants == 2
    assert isinstance(booking.participants, int)


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"participants": True}, "participants"),
        ({"participants": "2"}, "participants"),
        ({"participants": 2.5}, "participants"),
        ({"id": None}, "id"),
        ({"paymentStatus": 1}, "paymentStatus"),
    ],
)
def test_parse_booking_invalid_field(override: dict[str, object], field: str) -> None:
    with pytest.raises(ApiResponseError) as exc:
        parse_booking({**BOOKING_JSON, **override})
    assert str(exc.value) == f"invalid response from the API: booking has no valid '{field}'"


def test_parse_booking_missing_id() -> None:
    data = {key: value for key, value in BOOKING_JSON.items() if key != "id"}
    with pytest.raises(ApiResponseError, match="booking has no valid 'id'"):
        parse_booking(data)


@pytest.mark.parametrize("data", [[], "x", None])
def test_parse_booking_not_an_object(data: object) -> None:
    with pytest.raises(ApiResponseError, match="booking is not an object"):
        parse_booking(data)


def test_create_booking(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(BOOKINGS_URL).respond(201, json=BOOKING_JSON)
    with ApiClient(BASE_URL, token="tok-123") as client:
        assert client.create_booking("activity-2", 2) == BOOKING
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer tok-123"
    body = json.loads(request.content)
    assert body == {"activityId": "activity-2", "participants": 2}
    assert type(body["participants"]) is int


@pytest.mark.parametrize(
    ("status", "message", "expected"),
    [
        (
            400,
            "Capacity exceeded. Available: 13, Requested: 20",
            "Capacity exceeded. Available: 13, Requested: 20",
        ),
        (402, "Payment could not be processed", "Payment could not be processed"),
        (404, "Activity not found", "Activity not found"),
        (500, "Internal error", "API error 500: Internal error"),
    ],
)
def test_create_booking_errors(
    respx_mock: respx.MockRouter, status: int, message: str, expected: str
) -> None:
    respx_mock.post(BOOKINGS_URL).respond(status, json={"message": message, "errors": []})
    with ApiClient(BASE_URL, token="t") as client, pytest.raises(ApiError) as exc:
        client.create_booking("activity-2", 20)
    assert exc.value.status_code == status
    assert str(exc.value) == expected


def test_create_booking_validation_error(respx_mock: respx.MockRouter) -> None:
    error = {"field": "participants", "message": "Participants must be at least 1"}
    respx_mock.post(BOOKINGS_URL).respond(
        400, json={"message": "Validation failed", "errors": [error]}
    )
    with ApiClient(BASE_URL, token="t") as client, pytest.raises(ApiError) as exc:
        client.create_booking("activity-2", 1)
    assert exc.value.status_code == 400
    assert exc.value.field_errors == (FieldError(**error),)


def test_create_booking_incomplete_response(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(BOOKINGS_URL).respond(201, json={"activityId": "activity-2"})
    with ApiClient(BASE_URL, token="t") as client, pytest.raises(ApiResponseError):
        client.create_booking("activity-2", 1)


# --- my bookings ---------------------------------------------------------------------

BOOKING_ACTIVITY_JSON: dict[str, object] = {
    "name": "City Bike Tour",
    "slug": "city-bike-tour",
    "price": 35,
    "date": "2100-12-20",
    "duration": 180,
    "location": "City Center",
    "status": "published",
}
SUMMARY_JSON: dict[str, object] = {**BOOKING_JSON, "activity": BOOKING_ACTIVITY_JSON}
SUMMARY = BookingSummary(
    booking=BOOKING,
    activity=BookingActivity(
        name="City Bike Tour", date="2100-12-20", price=35.0, status="published"
    ),
)


def test_parse_booking_summary() -> None:
    assert parse_booking_summary(SUMMARY_JSON) == SUMMARY


def test_parse_booking_summary_without_payment_status() -> None:
    data = {key: value for key, value in SUMMARY_JSON.items() if key != "paymentStatus"}
    assert parse_booking_summary(data).booking.payment_status == "pending"


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({key: value for key, value in SUMMARY_JSON.items() if key != "activity"}, "activity"),
        ({**SUMMARY_JSON, "activity": "activity-2"}, "activity"),
        ({**SUMMARY_JSON, "activity": {**BOOKING_ACTIVITY_JSON, "price": True}}, "activity.price"),
        (
            {
                **SUMMARY_JSON,
                "activity": {k: v for k, v in BOOKING_ACTIVITY_JSON.items() if k != "name"},
            },
            "activity.name",
        ),
    ],
)
def test_parse_booking_summary_invalid_activity(data: dict[str, object], field: str) -> None:
    with pytest.raises(ApiResponseError) as exc:
        parse_booking_summary(data, 1)
    assert str(exc.value) == (
        f"invalid response from the API: booking booking-1 has no valid '{field}'"
    )


def test_parse_booking_summary_without_id_uses_position() -> None:
    data = {key: value for key, value in SUMMARY_JSON.items() if key != "id"}
    with pytest.raises(ApiResponseError, match="booking at position 3 has no valid 'id'"):
        parse_booking_summary(data, 3)


def test_parse_booking_summary_not_an_object() -> None:
    with pytest.raises(ApiResponseError, match="booking at position 2 is not an object"):
        parse_booking_summary("booking-1", 2)


def test_list_bookings(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(BOOKINGS_URL).respond(200, json=[SUMMARY_JSON])
    with ApiClient(BASE_URL, token="tok-123") as client:
        assert client.list_bookings() == [SUMMARY]
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer tok-123"
    assert "activityId" not in request.url.params


def test_list_bookings_for_activity(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(BOOKINGS_URL).respond(200, json=[SUMMARY_JSON])
    with ApiClient(BASE_URL, token="t") as client:
        client.list_bookings("activity-2")
    assert route.calls.last.request.url.params["activityId"] == "activity-2"


def test_list_bookings_empty(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKINGS_URL).respond(200, json=[])
    with ApiClient(BASE_URL, token="t") as client:
        assert client.list_bookings() == []


def test_list_bookings_not_a_list(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKINGS_URL).respond(200, json={"id": "booking-1"})
    with (
        ApiClient(BASE_URL, token="t") as client,
        pytest.raises(ApiResponseError, match="expected a list of bookings"),
    ):
        client.list_bookings()


def test_list_bookings_invalid_item(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(BOOKINGS_URL).respond(200, json=[SUMMARY_JSON, {"id": "booking-2"}])
    with (
        ApiClient(BASE_URL, token="t") as client,
        pytest.raises(ApiResponseError, match="booking booking-2 has no valid"),
    ):
        client.list_bookings()


@pytest.mark.parametrize(
    ("status", "message", "expected"),
    [
        (
            401,
            "Invalid or expired token. Please login again.",
            "Invalid or expired token. Please login again.",
        ),
        (500, "Failed to retrieve bookings", "API error 500: Failed to retrieve bookings"),
    ],
)
def test_list_bookings_errors(
    respx_mock: respx.MockRouter, status: int, message: str, expected: str
) -> None:
    respx_mock.get(BOOKINGS_URL).respond(status, json={"message": message, "errors": []})
    with ApiClient(BASE_URL, token="t") as client, pytest.raises(ApiError) as exc:
        client.list_bookings()
    assert exc.value.status_code == status
    assert str(exc.value) == expected
