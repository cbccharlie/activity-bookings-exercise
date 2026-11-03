"""Application errors and the helper that turns them into exit codes."""

import functools
from collections.abc import Callable
from dataclasses import dataclass

import typer

from activity_bookings.console import err_console


class ActivityBookingsError(Exception):
    """Base class for expected application errors shown to the user."""


class ConfigError(ActivityBookingsError):
    """The client configuration is missing or invalid."""


@dataclass(frozen=True)
class FieldError:
    """A validation error reported by the API for a single request field."""

    field: str
    message: str


class ApiError(ActivityBookingsError):
    """The API answered with an error status (4xx or 5xx).

    `message` is the headline shown to the user; each field error is shown on its own line.
    """

    def __init__(
        self, status_code: int, message: str, field_errors: tuple[FieldError, ...] = ()
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.field_errors = field_errors
        lines = [message, *(f"  - {error.field}: {error.message}" for error in field_errors)]
        super().__init__("\n".join(lines))


class ApiConnectionError(ActivityBookingsError):
    """The API could not be reached or did not answer in time."""


class ApiResponseError(ActivityBookingsError):
    """The API answered successfully but with a body the client does not understand."""


class SessionError(ActivityBookingsError):
    """The local session file could not be written."""


def handle_errors[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Print `Error: <message>` to stderr and exit with code 1 on ActivityBookingsError."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except ActivityBookingsError as exc:
            err_console.print(
                f"Error: {exc}", style="red", markup=False, highlight=False, soft_wrap=True
            )
            raise typer.Exit(code=1) from None

    return wrapper
