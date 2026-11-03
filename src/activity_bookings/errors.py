"""Application errors and the helper that turns them into exit codes."""

import functools
from collections.abc import Callable

import typer

from activity_bookings.console import err_console


class ActivityBookingsError(Exception):
    """Base class for expected application errors shown to the user."""


class ConfigError(ActivityBookingsError):
    """The client configuration is missing or invalid."""


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
