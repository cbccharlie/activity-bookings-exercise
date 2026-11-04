import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest
import respx
from jwt_helpers import make_jwt
from typer.testing import CliRunner, Result

from activity_bookings import cli
from activity_bookings.api_client import User
from activity_bookings.cli import app
from activity_bookings.config import DEFAULT_API_URL
from activity_bookings.interactive import Choice, MenuItem, Section, menu_items
from activity_bookings.session import Session, default_session_path, save_session

TOKEN = make_jwt(4102444800)  # exp in 2100
ACTIVITIES_URL = f"{DEFAULT_API_URL}/activities"
BOOKINGS_URL = f"{DEFAULT_API_URL}/bookings"
MENU = "What do you want to do?"

type Answer = str | bool | None


@dataclass
class FakePrompter:
    """Replays scripted answers in order and records every question."""

    answers: list[Answer]
    asked: list[tuple[str, str]] = field(default_factory=list)
    menus: list[Sequence[MenuItem]] = field(default_factory=list)

    def _next(self, kind: str, message: str) -> Answer:
        self.asked.append((kind, message))
        assert self.answers, f"unexpected {kind} prompt: {message!r}"
        return self.answers.pop(0)

    def select(self, message: str, items: Sequence[MenuItem]) -> str | None:
        if message == MENU:
            self.menus.append(items)
        answer = self._next("select", message)
        assert answer is None or isinstance(answer, str)
        return answer

    def text(self, message: str, default: str = "") -> str | None:
        answer = self._next("text", message)
        assert answer is None or isinstance(answer, str)
        return answer

    def confirm(self, message: str) -> bool | None:
        answer = self._next("confirm", message)
        assert answer is None or isinstance(answer, bool)
        return answer

    @property
    def menu_count(self) -> int:
        return len(self.menus)

    def confirmed(self) -> bool:
        return any(kind == "confirm" for kind, _ in self.asked)


type RunMenu = Callable[..., tuple[Result, FakePrompter]]


@pytest.fixture
def menu(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> RunMenu:
    """Run `activity-bookings [args]` in a fake terminal, answering the menu with `answers`."""

    def run(
        *answers: Answer, args: Sequence[str] = (), input: str | None = None
    ) -> tuple[Result, FakePrompter]:
        prompter = FakePrompter(list(answers))
        monkeypatch.setattr(cli, "_is_interactive", lambda: True)
        monkeypatch.setattr(cli, "_make_prompter", lambda: prompter)
        result = runner.invoke(app, list(args), input=input)
        assert prompter.answers == [], f"unused answers: {prompter.answers}"
        return result, prompter

    return run


def login_as(username: str = "Ana") -> Path:
    user = User(id="user-1", username=username, email="ana@example.com")
    return save_session(Session(api_url=DEFAULT_API_URL, access_token=TOKEN, user=user))


@pytest.fixture
def session_path() -> Path:
    return login_as()


def activity(**overrides: object) -> dict[str, object]:
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
    }
    data.update(overrides)
    return data


def booking(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "booking-1",
        "activityId": "activity-2",
        "userId": "user-1",
        "participants": 2,
        "createdAt": "2100-11-03T10:00:00.000Z",
        "paymentId": "payment-1",
        "paymentStatus": "paid",
    }
    data.update(overrides)
    return data


def sent_json(route: respx.Route) -> object:
    return json.loads(route.calls.last.request.content)


def assert_clean_exit(result: Result) -> None:
    assert result.exit_code == 0, result.output
    assert "Traceback" not in result.output


# --- Menú principal ------------------------------------------------------------------


def test_menu_options_in_order(menu: RunMenu) -> None:
    _, prompter = menu("exit")
    labels = [
        f"[{item.title}]" if isinstance(item, Section) else item.label for item in prompter.menus[0]
    ]
    assert labels == [
        "[Activities]",
        "List activities",
        "Show an activity",
        "Create an activity",
        "Update an activity",
        "Delete an activity",
        "Change an activity's status",
        "[Bookings]",
        "Book an activity",
        "My bookings",
        "Show a booking",
        "[Account]",
        "Register",
        "Log in",
        "Log out",
        "Who am I",
        "[Settings]",
        "Show configuration",
        "Exit",
    ]
    assert menu_items()[-1] == Choice("Exit", "exit")


# --- Indicación de la sesión ---------------------------------------------------------


def test_header_without_session(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    result, _ = menu("exit")
    assert_clean_exit(result)
    assert "Not logged in" in result.stdout
    assert respx_mock.calls.call_count == 0


@pytest.mark.usefixtures("session_path")
def test_header_with_session(menu: RunMenu) -> None:
    result, _ = menu("exit")
    assert "Logged in as Ana" in result.stdout


def test_header_with_corrupt_session(menu: RunMenu) -> None:
    path = default_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json", encoding="utf-8")
    result, _ = menu("exit")
    assert_clean_exit(result)
    assert "Not logged in" in result.stdout


# --- Navegación y salida -------------------------------------------------------------


def test_cancel_menu_exits(menu: RunMenu) -> None:
    result, prompter = menu(None)
    assert_clean_exit(result)
    assert prompter.menu_count == 1


def test_back_to_menu_after_action(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).respond(200, json=[activity()])
    result, prompter = menu("activities.list", "", "any", "exit")
    assert_clean_exit(result)
    assert prompter.menu_count == 2
    assert result.stdout.count("Not logged in") == 2


# --- Acciones del menú ---------------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_cancel_inside_action(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    result, prompter = menu("activities.create", "Yoga", None, "exit")
    assert_clean_exit(result)
    assert respx_mock.calls.call_count == 0
    assert prompter.menu_count == 2


# --- Consulta de actividades ---------------------------------------------------------


def test_list_activities_with_filters(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    draft = activity(id="activity-7", name="Draft Bike Ride", status="draft")
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[activity(), draft])
    result, _ = menu("activities.list", "bike", "published", "exit")
    assert_clean_exit(result)
    assert route.calls.last.request.url.params["q"] == "bike"
    assert "City Bike Tour" in result.stdout
    assert "Draft Bike Ride" not in result.stdout  # --status published was passed


def test_list_activities_without_filters(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ACTIVITIES_URL).respond(200, json=[])
    result, _ = menu("activities.list", "", "any", "exit")
    assert_clean_exit(result)
    assert "q" not in route.calls.last.request.url.params


def test_show_activity(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{ACTIVITIES_URL}/activity-2").respond(200, json=activity())
    result, _ = menu("activities.show", "activity-2", "exit")
    assert_clean_exit(result)
    assert route.call_count == 1
    assert "City Bike Tour" in result.stdout
    assert "180 min" in result.stdout


# --- Alta y modificación de actividades ----------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_create_activity_without_duration(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(ACTIVITIES_URL).respond(
        201, json=activity(id="activity-5", name="Yoga", status="draft")
    )
    result, _ = menu("activities.create", "Yoga", "20", "2027-01-15", "Park", "2", "10", "", "exit")
    assert_clean_exit(result)
    assert sent_json(route) == {
        "name": "Yoga",
        "price": 20,
        "date": "2027-01-15",
        "location": "Park",
        "minParticipants": 2,
        "maxParticipants": 10,
    }
    assert "Activity activity-5 created." in result.stdout


@pytest.mark.usefixtures("session_path")
def test_update_only_price(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.put(f"{ACTIVITIES_URL}/activity-5").respond(
        200, json=activity(id="activity-5", price=25)
    )
    result, _ = menu("activities.update", "activity-5", "", "25", "", "", "", "", "", "exit")
    assert_clean_exit(result)
    assert sent_json(route) == {"price": 25}
    assert "Activity activity-5 updated." in result.stdout


# --- Borrado y cambio de estado desde el menú ----------------------------------------


@pytest.mark.usefixtures("session_path")
def test_delete_confirmed(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.delete(f"{ACTIVITIES_URL}/activity-5").respond(204)
    result, _ = menu("activities.delete", "activity-5", True, "exit")
    assert_clean_exit(result)
    assert route.call_count == 1
    assert "Activity activity-5 deleted." in result.stdout


@pytest.mark.usefixtures("session_path")
def test_delete_rejected(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    result, prompter = menu("activities.delete", "activity-5", False, "exit")
    assert_clean_exit(result)
    assert respx_mock.calls.call_count == 0
    assert "Deletion cancelled." in result.stdout
    assert prompter.menu_count == 2


@pytest.mark.usefixtures("session_path")
def test_publish_without_confirmation(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.patch(f"{ACTIVITIES_URL}/activity-5/status").respond(
        200, json=activity(id="activity-5", status="published")
    )
    result, prompter = menu("activities.status", "activity-5", "published", "exit")
    assert_clean_exit(result)
    assert not prompter.confirmed()
    assert sent_json(route) == {"status": "published"}
    assert "Activity activity-5 is now published." in result.stdout


@pytest.mark.usefixtures("session_path")
def test_cancel_status_rejected(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    result, prompter = menu("activities.status", "activity-5", "cancelled", False, "exit")
    assert_clean_exit(result)
    assert prompter.confirmed()
    assert respx_mock.calls.call_count == 0
    assert "Status change cancelled." in result.stdout


# --- Acciones sobre reservas, cuenta y configuración ---------------------------------


@pytest.mark.usefixtures("session_path")
def test_show_booking(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    detail = booking(activity={**activity(), "duration": 120})
    route = respx_mock.get(f"{BOOKINGS_URL}/booking-1").respond(200, json=detail)
    result, _ = menu("bookings.show", "booking-1", "exit")
    assert_clean_exit(result)
    assert route.call_count == 1
    assert "payment-1" in result.stdout
    assert "120 min" in result.stdout


@pytest.mark.usefixtures("session_path")
def test_my_bookings_without_filter(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(BOOKINGS_URL).respond(200, json=[])
    result, _ = menu("bookings.list", "", "exit")
    assert_clean_exit(result)
    assert "activityId" not in route.calls.last.request.url.params
    assert "No bookings found." in result.stdout


@pytest.mark.usefixtures("session_path")
def test_book_two_seats(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{ACTIVITIES_URL}/activity-2").respond(200, json=activity())
    route = respx_mock.post(BOOKINGS_URL).respond(201, json=booking())
    result, _ = menu("bookings.create", "activity-2", "2", "exit", input="y\n")
    assert_clean_exit(result)
    assert sent_json(route) == {"activityId": "activity-2", "participants": 2}
    assert "Booking booking-1 created." in result.stdout


def test_log_out(menu: RunMenu, respx_mock: respx.MockRouter, session_path: Path) -> None:
    result, _ = menu("auth.logout", "exit")
    assert_clean_exit(result)
    assert not session_path.exists()
    assert respx_mock.calls.call_count == 0
    assert "Not logged in" in result.stdout


def test_show_configuration(menu: RunMenu) -> None:
    result, _ = menu("config", "exit")
    assert_clean_exit(result)
    assert "API URL" in result.stdout


# --- Errores dentro del menú ---------------------------------------------------------


@pytest.mark.usefixtures("session_path")
def test_api_error_back_to_menu(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{ACTIVITIES_URL}/activity-99").respond(
        404, json={"message": "Activity not found", "errors": []}
    )
    result, prompter = menu("activities.show", "activity-99", "exit")
    assert_clean_exit(result)
    assert "Error: Activity not found" in result.stderr
    assert prompter.menu_count == 2


@pytest.mark.usefixtures("session_path")
def test_invalid_value_back_to_menu(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    result, prompter = menu(
        "activities.create", "Yoga", "abc", "2027-01-15", "Park", "2", "10", "", "exit"
    )
    assert_clean_exit(result)
    assert "--price" in result.stderr
    assert respx_mock.calls.call_count == 0
    assert prompter.menu_count == 2


def test_protected_action_without_session(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    result, prompter = menu("bookings.list", "", "exit")
    assert_clean_exit(result)
    assert "Error: not logged in" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0
    assert prompter.menu_count == 2


def test_api_down_inside_menu(menu: RunMenu, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ACTIVITIES_URL).mock(side_effect=httpx.ConnectError("refused"))
    result, _ = menu("activities.list", "", "any", "exit")
    assert_clean_exit(result)
    assert "Error: cannot connect to the API at http://localhost:3000" in result.stderr


# --- Configuración en el menú --------------------------------------------------------


def test_menu_uses_config_option(
    menu: RunMenu, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    config = tmp_path / "custom.toml"
    config.write_text('api_url = "http://api.example.com"\n', encoding="utf-8")
    route = respx_mock.get("http://api.example.com/activities").respond(200, json=[])
    result, _ = menu("activities.list", "", "any", "exit", args=["--config", str(config)])
    assert_clean_exit(result)
    assert route.call_count == 1
