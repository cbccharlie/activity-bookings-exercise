"""`bookings` command group: book seats in activities and list or show your bookings."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from activity_bookings.api_client import Activity, Booking, BookingDetail, BookingSummary
from activity_bookings.booking_rules import check_bookable
from activity_bookings.commands._auth import authorized_client, login_hint
from activity_bookings.commands.activities_cmd import (
    _format_date,
    _format_duration,
    _format_price,
)
from activity_bookings.config import load_settings
from activity_bookings.console import console
from activity_bookings.errors import ActivityBookingsError, ApiError, handle_errors

app = typer.Typer(
    help="Book seats in activities and list or show your bookings.", no_args_is_help=True
)


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


@app.command("list")
@handle_errors
def list_(
    ctx: typer.Context,
    activity: Annotated[
        str | None,
        typer.Option(
            "--activity", metavar="ACTIVITY_ID", help="Show only bookings of this activity."
        ),
    ] = None,
) -> None:
    """List your bookings with their activity, total and status. Requires a session.

    The total is the activity's current price x seats; the API does not store the amount paid.
    """
    if activity is not None:
        activity = activity.strip()
        if not activity:
            raise typer.BadParameter("cannot be empty", param_hint="--activity")
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)
    with (
        authorized_client(settings) as client,
        login_hint(),
        _deleted_activity_hint("One of your bookings may refer to a deleted activity."),
    ):
        bookings = client.list_bookings(activity)
    if not bookings:
        console.print("No bookings found.", markup=False, highlight=False)
        return
    console.print(_bookings_table(bookings), markup=False, highlight=False)
    count = len(bookings)
    console.print(f"{count} {'booking' if count == 1 else 'bookings'}", highlight=False)


@app.command("show")
@handle_errors
def show(
    ctx: typer.Context,
    booking_id: Annotated[
        str, typer.Argument(metavar="BOOKING_ID", help="ID of the booking, e.g. booking-1.")
    ],
) -> None:
    """Show one of your bookings with its activity, total and payment. Requires a session.

    The total is the activity's current price x seats; the API does not store the amount paid.
    """
    booking_id = booking_id.strip()
    if not booking_id:
        raise typer.BadParameter("BOOKING_ID cannot be empty", param_hint="BOOKING_ID")
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)
    with (
        authorized_client(settings) as client,
        login_hint(),
        _deleted_activity_hint("This booking may refer to a deleted activity."),
    ):
        detail = client.get_booking(booking_id)
    console.print(_booking_detail_table(detail), markup=False, highlight=False)


@contextmanager
def _deleted_activity_hint(hint: str) -> Iterator[None]:
    """Add `hint`, the known cause of a 500 from the bookings API; other errors pass unchanged."""
    try:
        yield
    except ApiError as exc:
        if exc.status_code != 500:
            raise
        raise ActivityBookingsError(f"{exc}\n{hint}") from exc


def _booking_detail_table(detail: BookingDetail) -> Table:
    """The booking as a table without header: one row per field."""
    booking, activity = detail.summary.booking, detail.summary.activity
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column(style="bold", no_wrap=True)
    table.add_column(overflow="fold")
    table.add_row("ID", booking.id)
    table.add_row("Activity", f"{activity.name} ({booking.activity_id})")
    table.add_row("Date", _format_date(activity.date))
    table.add_row("Duration", _format_duration(detail.activity_duration))
    table.add_row("Location", detail.activity_location)
    table.add_row("Seats", str(booking.participants))
    table.add_row("Price", _format_price(activity.price))
    table.add_row("Total", _format_price(activity.price * booking.participants))
    table.add_row("Payment", booking.payment_status)
    if detail.payment_id is not None:
        table.add_row("Payment ID", detail.payment_id)
    table.add_row("Activity status", activity.status)
    table.add_row("Booked at", _format_date(booking.created_at))
    return table


def _bookings_table(bookings: list[BookingSummary]) -> Table:
    table = Table(title="My bookings")
    table.add_column("ID", no_wrap=True)
    table.add_column("Activity")
    table.add_column("Date", no_wrap=True)
    table.add_column("Seats", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Payment", no_wrap=True)
    table.add_column("Activity status", no_wrap=True)
    for summary in bookings:
        booking, activity = summary.booking, summary.activity
        table.add_row(
            booking.id,
            f"{activity.name} ({booking.activity_id})",
            _format_date(activity.date),
            str(booking.participants),
            _format_price(activity.price * booking.participants),
            booking.payment_status,
            activity.status,
        )
    return table


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
