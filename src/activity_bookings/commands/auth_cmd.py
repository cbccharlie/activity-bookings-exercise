"""`auth` command group: account registration and the local session."""

from pathlib import Path
from typing import Annotated

import typer

from activity_bookings.api_client import ApiClient
from activity_bookings.config import load_settings
from activity_bookings.console import console
from activity_bookings.errors import ActivityBookingsError, SessionError, handle_errors
from activity_bookings.session import Session, save_session

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

    session = Session(api_url=settings.api_url, access_token=result.access_token, user=result.user)
    try:
        path = save_session(session)
    except SessionError as exc:
        raise SessionError(f"account created, but {exc}") from exc

    user = result.user
    console.print(
        f"Account created for {user.username} ({user.email}).", markup=False, highlight=False
    )
    console.print(f"Logged in. Session saved to {path}", markup=False, highlight=False)
