"""`auth` command group: account registration and the local session."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from activity_bookings.api_client import ApiClient, AuthResult
from activity_bookings.config import load_settings
from activity_bookings.console import console
from activity_bookings.errors import ActivityBookingsError, SessionError, handle_errors
from activity_bookings.session import (
    Session,
    default_session_path,
    delete_session,
    load_session,
    save_session,
    token_expiry,
)

app = typer.Typer(help="Create an account and manage the local session.", no_args_is_help=True)


@app.command()
@handle_errors
def register(
    ctx: typer.Context,
    username: Annotated[
        str | None, typer.Option("--username", help="User name (prompted if omitted).")
    ] = None,
    email: Annotated[
        str | None, typer.Option("--email", help="Email address (prompted if omitted).")
    ] = None,
    accept_terms: Annotated[
        bool,
        typer.Option("--accept-terms", help="Accept the terms and conditions without asking."),
    ] = False,
) -> None:
    """Create an account and log in with it. The password is always prompted."""
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)

    username = username or typer.prompt("Username")
    email = email or typer.prompt("Email")
    password: str = typer.prompt("Password", hide_input=True, confirmation_prompt=True)
    if not accept_terms and not typer.confirm(
        "Do you accept the terms and conditions?", default=False
    ):
        raise ActivityBookingsError("you must accept the terms and conditions to register")

    with ApiClient(settings.api_url) as client:
        result = client.register(username, email, password)

    path = _save_session(result, settings.api_url, done="account created")

    user = result.user
    console.print(
        f"Account created for {user.username} ({user.email}).", markup=False, highlight=False
    )
    console.print(f"Logged in. Session saved to {path}", markup=False, highlight=False)


@app.command()
@handle_errors
def login(
    ctx: typer.Context,
    email: Annotated[
        str | None, typer.Option("--email", help="Email address (prompted if omitted).")
    ] = None,
) -> None:
    """Log in with an existing account. The password is always prompted."""
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)

    if email is None:
        email = typer.prompt("Email")
    password: str = typer.prompt("Password", hide_input=True)

    with ApiClient(settings.api_url) as client:
        result = client.login(email, password)

    path = _save_session(result, settings.api_url, done="logged in")

    user = result.user
    console.print(f"Logged in as {user.username} ({user.email}).", markup=False, highlight=False)
    console.print(f"Session saved to {path}", markup=False, highlight=False)


@app.command()
@handle_errors
def logout() -> None:
    """Remove the local session. The token is not revoked on the server."""
    if delete_session():
        console.print(
            f"Logged out. Session removed from {default_session_path()}",
            markup=False,
            highlight=False,
        )
    else:
        console.print("Not logged in.", markup=False, highlight=False)


@app.command()
@handle_errors
def whoami() -> None:
    """Show the logged-in user from the local session, without calling the API."""
    session = load_session()
    if session is None:
        raise ActivityBookingsError(
            "not logged in; run 'activity-bookings auth login' or 'activity-bookings auth register'"
        )

    expiry = token_expiry(session.access_token)
    expired = expiry is not None and expiry <= _now()
    if expiry is None:
        expires = "unknown"
    else:
        expires = expiry.strftime("%Y-%m-%d %H:%M UTC") + (" (expired)" if expired else "")

    user = session.user
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column(style="bold", no_wrap=True)
    table.add_column(overflow="fold")
    table.add_row("User", user.username)
    table.add_row("Email", user.email)
    table.add_row("User ID", str(user.id))
    table.add_row("API URL", session.api_url)
    table.add_row("Token expires", expires)
    console.print(table, markup=False, highlight=False)
    if expired:
        console.print(
            "Your session has expired. Run 'activity-bookings auth login' to start a new one.",
            markup=False,
            highlight=False,
        )


def _save_session(result: AuthResult, api_url: str, done: str) -> Path:
    """Save the session for `result`; on failure, say what already happened (`done`)."""
    session = Session(api_url=api_url, access_token=result.access_token, user=result.user)
    try:
        return save_session(session)
    except SessionError as exc:
        raise SessionError(f"{done}, but {exc}") from exc


def _now() -> datetime:
    return datetime.now(UTC)
