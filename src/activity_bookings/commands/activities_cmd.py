"""`activities` command group: browse the public activity catalogue."""

from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from activity_bookings.api_client import Activity, ApiClient
from activity_bookings.config import load_settings
from activity_bookings.console import console
from activity_bookings.errors import handle_errors

app = typer.Typer(help="Browse the activity catalogue.", no_args_is_help=True)


class SortField(StrEnum):
    """Fields the API can sort the listing by."""

    DATE = "date"
    PRICE = "price"
    NAME = "name"
    LOCATION = "location"


class SortOrder(StrEnum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


class ActivityStatus(StrEnum):
    """Activity states, used to filter the listing on the client."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CONFIRMED = "confirmed"
    SOLD_OUT = "sold-out"
    DONE = "done"
    CANCELLED = "cancelled"


@app.command("list")
@handle_errors
def list_activities(
    ctx: typer.Context,
    search: Annotated[
        str | None,
        typer.Option("--search", help="Text to search in name, location and slug (by the API)."),
    ] = None,
    sort: Annotated[
        SortField | None, typer.Option("--sort", help="Field to sort by (by the API).")
    ] = None,
    order: Annotated[
        SortOrder | None,
        typer.Option("--order", help="Sort direction (asc by default); requires --sort."),
    ] = None,
    status: Annotated[
        ActivityStatus | None,
        typer.Option("--status", help="Show only activities in this state (filtered locally)."),
    ] = None,
) -> None:
    """List activities, in every state unless --status is given. Capacity is the total size."""
    if search is not None and not search.strip():
        raise typer.BadParameter("--search cannot be empty", param_hint="'--search'")
    if order is not None and sort is None:
        raise typer.BadParameter("--order requires --sort", param_hint="'--order'")

    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)
    with ApiClient(settings.api_url) as client:
        activities = client.list_activities(
            search=search,
            sort=None if sort is None else sort.value,
            order=(order or SortOrder.ASC).value,
        )

    if status is not None:
        activities = [activity for activity in activities if activity.status == status.value]
    if not activities:
        console.print("No activities found.", markup=False, highlight=False)
        return
    console.print(_activities_table(activities), markup=False, highlight=False)
    count = len(activities)
    console.print(f"{count} {'activity' if count == 1 else 'activities'}", highlight=False)


def _activities_table(activities: list[Activity]) -> Table:
    table = Table(title="Activities")
    table.add_column("ID", no_wrap=True)
    table.add_column("Name")
    table.add_column("Date", no_wrap=True)
    table.add_column("Location")
    table.add_column("Price", justify="right")
    table.add_column("Capacity", justify="right")
    table.add_column("Status", no_wrap=True)
    for activity in activities:
        table.add_row(
            activity.id,
            activity.name,
            _format_date(activity.date),
            activity.location,
            _format_price(activity.price),
            str(activity.max_participants),
            activity.status,
        )
    return table


def _format_date(value: str) -> str:
    """Show a date-only value as is and a date-time as `YYYY-MM-DD HH:MM UTC`."""
    try:
        date.fromisoformat(value)
        return value
    except ValueError:
        pass
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return value
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _format_price(value: float) -> str:
    """Show a price with two decimals and no currency (the API does not give one)."""
    return f"{value:.2f}"
