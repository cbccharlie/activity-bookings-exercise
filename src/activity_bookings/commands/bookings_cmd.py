"""`bookings` command group: book seats in activities."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from activity_bookings.api_client import Activity, Booking
from activity_bookings.booking_rules import check_bookable
from activity_bookings.commands._auth import authorized_client, login_hint
from activity_bookings.commands.activities_cmd import _format_date, _format_price
from activity_bookings.config import load_settings
from activity_bookings.console import console
from activity_bookings.errors import handle_errors

app = typer.Typer(help="Book seats in activities.", no_args_is_help=True)


@app.command("create")
@handle_errors
def create_booking(
    ctx: typer.Context,
    activity_id: Annotated[
        str, typer.Argument(metavar="ACTIVITY_ID", help="ID of the activity, e.g. activity-2.")
    ],
    participants: Annotated[
        int, typer.Option("--participants", "-p", min=1, help="Number of seats to book.")
    ] = 1,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Book without asking for confirmation.")
    ] = False,
) -> None:
    """Book seats in a published activity that has not taken place yet. Requires a session.

    The API charges price x seats at once and bookings cannot be cancelled.
    """
    activity_id = activity_id.strip()
    if not activity_id:
        raise typer.BadParameter("ACTIVITY_ID cannot be empty", param_hint="ACTIVITY_ID")
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)
    with authorized_client(settings) as client, login_hint():
        activity = client.get_activity(activity_id).activity
        check_bookable(activity, _now())
        total = _format_price(activity.price * participants)
        if not yes and not typer.confirm(
            f"Book {participants} seat(s) for {activity.name} ({activity.id}) on "
            f"{_format_date(activity.date)} for a total of {total}?",
            default=False,
        ):
            console.print("Booking cancelled.", markup=False, highlight=False)
            return
        booking = client.create_booking(activity.id, participants)
    _print_booking(booking, activity, total)


def _now() -> datetime:
    return datetime.now(UTC)


def _print_booking(booking: Booking, activity: Activity, total: str) -> None:
    """Print `Booking <id> created.` and the booking as a table without header."""
    console.print(f"Booking {booking.id} created.", markup=False, highlight=False)
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column(style="bold", no_wrap=True)
    table.add_column(overflow="fold")
    table.add_row("ID", booking.id)
    table.add_row("Activity", f"{activity.name} ({activity.id})")
    table.add_row("Date", _format_date(activity.date))
    table.add_row("Participants", str(booking.participants))
    table.add_row("Total", total)
    table.add_row("Payment", booking.payment_status)
    console.print(table, markup=False, highlight=False)
