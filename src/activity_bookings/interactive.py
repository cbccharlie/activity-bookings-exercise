"""Interactive menu: pick an action with the arrow keys and run the matching subcommand.

The menu only collects data and builds the subcommand's arguments; validation, API calls,
session checks, errors and output are those of the subcommand itself.
"""

import contextlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import questionary

from activity_bookings.commands.activities_cmd import FINAL_STATUSES, ActivityStatus
from activity_bookings.console import console
from activity_bookings.errors import SessionError
from activity_bookings.session import load_session

type Execute = Callable[[list[str]], None]
"""Run the CLI with these arguments (e.g. `["activities", "list"]`) and return when it ends."""


@dataclass(frozen=True)
class Choice:
    """A selectable option: the label shown and the value returned."""

    label: str
    value: str


@dataclass(frozen=True)
class Section:
    """A non-selectable heading that groups the options after it."""

    title: str


type MenuItem = Choice | Section


class Prompter(Protocol):
    """Asks the user for input. Every method returns None if the user cancels (Esc, Ctrl+C)."""

    def select(self, message: str, items: Sequence[MenuItem]) -> str | None: ...

    def text(self, message: str, default: str = "") -> str | None: ...

    def confirm(self, message: str) -> bool | None: ...


class QuestionaryPrompter:
    """Prompter for a real terminal, with arrow-key selection."""

    def select(self, message: str, items: Sequence[MenuItem]) -> str | None:
        choices: list[questionary.Choice | questionary.Separator] = [
            questionary.Separator(f"── {item.title} ──")
            if isinstance(item, Section)
            else questionary.Choice(item.label, value=item.value)
            for item in items
        ]
        answer = questionary.select(message, choices=choices).ask()
        return answer if isinstance(answer, str) else None

    def text(self, message: str, default: str = "") -> str | None:
        answer = questionary.text(message, default=default).ask()
        return answer if isinstance(answer, str) else None

    def confirm(self, message: str) -> bool | None:
        answer = questionary.confirm(message, default=False).ask()
        return answer if isinstance(answer, bool) else None


class _Cancelled(Exception):
    """The user cancelled a prompt: go back to the menu without running anything."""


@dataclass(frozen=True)
class _Ask:
    """Prompts that raise _Cancelled instead of returning None."""

    prompter: Prompter

    def text(self, message: str, default: str = "") -> str:
        answer = self.prompter.text(message, default)
        if answer is None:
            raise _Cancelled
        return answer.strip()

    def choose(self, message: str, items: Sequence[MenuItem]) -> str:
        answer = self.prompter.select(message, items)
        if answer is None:
            raise _Cancelled
        return answer

    def confirm(self, message: str) -> bool:
        answer = self.prompter.confirm(message)
        if answer is None:
            raise _Cancelled
        return answer


type _Action = Callable[[_Ask, Execute], None]

ANY_STATUS = "any"
EXIT = "exit"
DATE_PROMPT = "Date (YYYY-MM-DD, or ISO 8601 with time and zone):"
ACTIVITY_FIELDS = (
    ("Name:", "--name"),
    ("Price:", "--price"),
    (DATE_PROMPT, "--date"),
    ("Location:", "--location"),
    ("Minimum participants:", "--min-participants"),
    ("Maximum participants:", "--max-participants"),
)


def _optional(option: str, value: str) -> list[str]:
    """`[option, value]`, or nothing if the value was left empty."""
    return [option, value] if value else []


def _status_choices() -> list[MenuItem]:
    return [Choice(status.value, status.value) for status in ActivityStatus]


def _list_activities(ask: _Ask, execute: Execute) -> None:
    search = ask.text("Search text (empty for all):")
    status = ask.choose("Status:", [Choice("any", ANY_STATUS), *_status_choices()])
    status_args = [] if status == ANY_STATUS else ["--status", status]
    execute(["activities", "list", *_optional("--search", search), *status_args])


def _show_activity(ask: _Ask, execute: Execute) -> None:
    execute(["activities", "show", ask.text("Activity ID:")])


def _create_activity(ask: _Ask, execute: Execute) -> None:
    args = ["activities", "create"]
    for message, option in ACTIVITY_FIELDS:
        args += [option, ask.text(message)]
    args += _optional("--duration", ask.text("Duration in minutes (empty for the API default):"))
    execute(args)


def _update_activity(ask: _Ask, execute: Execute) -> None:
    args = ["activities", "update", ask.text("Activity ID:")]
    console.print("Leave a field empty to keep its value.", markup=False, highlight=False)
    for message, option in (*ACTIVITY_FIELDS, ("Duration in minutes:", "--duration")):
        args += _optional(option, ask.text(message))
    execute(args)


def _delete_activity(ask: _Ask, execute: Execute) -> None:
    activity_id = ask.text("Activity ID:")
    if not ask.confirm(f"Delete activity {activity_id}?"):
        console.print("Deletion cancelled.", markup=False, highlight=False)
        return
    execute(["activities", "delete", activity_id, "--yes"])


def _change_status(ask: _Ask, execute: Execute) -> None:
    activity_id = ask.text("Activity ID:")
    status = ask.choose("New status:", _status_choices())
    if status in FINAL_STATUSES and not ask.confirm(
        f"Change activity {activity_id} to {status}? This cannot be undone."
    ):
        console.print("Status change cancelled.", markup=False, highlight=False)
        return
    execute(["activities", "status", activity_id, status, "--yes"])


def _book_activity(ask: _Ask, execute: Execute) -> None:
    activity_id = ask.text("Activity ID:")
    seats = ask.text("Seats:", default="1")
    execute(["bookings", "create", activity_id, "--participants", seats])


def _my_bookings(ask: _Ask, execute: Execute) -> None:
    activity_id = ask.text("Only bookings of activity ID (empty for all):")
    execute(["bookings", "list", *_optional("--activity", activity_id)])


def _show_booking(ask: _Ask, execute: Execute) -> None:
    execute(["bookings", "show", ask.text("Booking ID:")])


def _register(ask: _Ask, execute: Execute) -> None:
    username = ask.text("Username:")
    email = ask.text("Email:")
    execute(["auth", "register", "--username", username, "--email", email])


def _log_in(ask: _Ask, execute: Execute) -> None:
    execute(["auth", "login", "--email", ask.text("Email:")])


def _run(*args: str) -> _Action:
    """An action without data: just run the subcommand."""

    def action(ask: _Ask, execute: Execute) -> None:
        execute(list(args))

    return action


_ACTIONS: dict[str, tuple[str, _Action]] = {
    "activities.list": ("List activities", _list_activities),
    "activities.show": ("Show an activity", _show_activity),
    "activities.create": ("Create an activity", _create_activity),
    "activities.update": ("Update an activity", _update_activity),
    "activities.delete": ("Delete an activity", _delete_activity),
    "activities.status": ("Change an activity's status", _change_status),
    "bookings.create": ("Book an activity", _book_activity),
    "bookings.list": ("My bookings", _my_bookings),
    "bookings.show": ("Show a booking", _show_booking),
    "auth.register": ("Register", _register),
    "auth.login": ("Log in", _log_in),
    "auth.logout": ("Log out", _run("auth", "logout")),
    "auth.whoami": ("Who am I", _run("auth", "whoami")),
    "config": ("Show configuration", _run("config")),
}

_SECTIONS = (
    ("Activities", "activities."),
    ("Bookings", "bookings."),
    ("Account", "auth."),
    ("Settings", "config"),
)


def menu_items() -> list[MenuItem]:
    """The main menu: one section per command group, then Exit."""
    items: list[MenuItem] = []
    for title, prefix in _SECTIONS:
        items.append(Section(title))
        items += [
            Choice(label, key) for key, (label, _) in _ACTIONS.items() if key.startswith(prefix)
        ]
    items.append(Choice("Exit", EXIT))
    return items


def session_header() -> str:
    """`Logged in as <username>` or `Not logged in`, from the saved session (no API call)."""
    try:
        session = load_session()
    except SessionError:
        session = None
    return "Not logged in" if session is None else f"Logged in as {session.user.username}"


def run_menu(prompter: Prompter, execute: Execute) -> None:
    """Show the menu until the user picks Exit or cancels it."""
    ask = _Ask(prompter)
    items = menu_items()
    while True:
        console.print(session_header(), markup=False, highlight=False)
        choice = prompter.select("What do you want to do?", items)
        if choice is None or choice == EXIT:
            return
        _, action = _ACTIONS[choice]
        with contextlib.suppress(_Cancelled):
            action(ask, execute)
        console.print()
