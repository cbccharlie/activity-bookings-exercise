"""`activities` command group: browse the catalogue and manage your own activities."""

from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from activity_bookings.api_client import (
    Activity,
    ActivityChanges,
    ActivityDetail,
    ApiClient,
    NewActivity,
)
from activity_bookings.commands._auth import authorized_client, login_hint
from activity_bookings.config import load_settings
from activity_bookings.console import console
from activity_bookings.errors import handle_errors

app = typer.Typer(
    help="Browse the activity catalogue and manage your own activities.", no_args_is_help=True
)

DATE_HELP = (
    "Date as YYYY-MM-DD or ISO 8601 with time and zone (e.g. 2027-01-15T10:00:00Z); "
    "must be in the future."
)


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
    """Activity states: filter for the listing and target of `activities status`."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CONFIRMED = "confirmed"
    SOLD_OUT = "sold-out"
    DONE = "done"
    CANCELLED = "cancelled"


FINAL_STATUSES = frozenset({ActivityStatus.DONE, ActivityStatus.CANCELLED})


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


@app.command("show")
@handle_errors
def show_activity(
    ctx: typer.Context,
    activity_id: Annotated[
        str, typer.Argument(metavar="ACTIVITY_ID", help="ID of the activity, e.g. activity-2.")
    ],
) -> None:
    """Show all the details of one activity. Capacity is the total size, not free places."""
    if not activity_id.strip():
        raise typer.BadParameter("ACTIVITY_ID cannot be empty", param_hint="ACTIVITY_ID")
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)
    with ApiClient(settings.api_url) as client:
        detail = client.get_activity(activity_id.strip())
    console.print(_detail_table(detail), markup=False, highlight=False)


def _detail_table(detail: ActivityDetail) -> Table:
    activity = detail.activity
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column(style="bold", no_wrap=True)
    table.add_column(overflow="fold")
    table.add_row("ID", activity.id)
    table.add_row("Name", activity.name)
    table.add_row("Slug", detail.slug)
    table.add_row("Date", _format_date(activity.date))
    table.add_row("Duration", _format_duration(detail.duration))
    table.add_row("Location", activity.location)
    table.add_row("Price", _format_price(activity.price))
    table.add_row("Min participants", str(detail.min_participants))
    table.add_row("Capacity", str(activity.max_participants))
    table.add_row("Status", activity.status)
    table.add_row("Organizer", detail.user_id)
    table.add_row("Created", _format_date(detail.created_at))
    if detail.updated_at is not None:
        table.add_row("Updated", _format_date(detail.updated_at))
    return table


def _format_duration(minutes: int) -> str:
    """Show a duration in minutes, e.g. `120 min`."""
    return f"{minutes} min"


@app.command("create")
@handle_errors
def create_activity(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", help="Activity name.")],
    price: Annotated[float, typer.Option("--price", help="Price per participant.")],
    date: Annotated[str, typer.Option("--date", help=DATE_HELP)],
    location: Annotated[str, typer.Option("--location", help="Where it takes place.")],
    min_participants: Annotated[
        int, typer.Option("--min-participants", help="Minimum number of participants.")
    ],
    max_participants: Annotated[
        int, typer.Option("--max-participants", help="Maximum number of participants.")
    ],
    duration: Annotated[
        int | None,
        typer.Option("--duration", help="Duration in minutes (the API uses 60 if omitted)."),
    ] = None,
) -> None:
    """Create an activity owned by you. It starts as a draft. Requires a session."""
    new_activity = NewActivity(
        name=name,
        price=price,
        date=date,
        location=location,
        min_participants=min_participants,
        max_participants=max_participants,
        duration=duration,
    )
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)
    with authorized_client(settings) as client, login_hint():
        created = client.create_activity(new_activity)
    _print_activity(created, "created")


@app.command("update")
@handle_errors
def update_activity(
    ctx: typer.Context,
    activity_id: Annotated[
        str, typer.Argument(metavar="ACTIVITY_ID", help="ID of the activity to change.")
    ],
    name: Annotated[str | None, typer.Option("--name", help="New name.")] = None,
    price: Annotated[float | None, typer.Option("--price", help="New price.")] = None,
    date: Annotated[str | None, typer.Option("--date", help=DATE_HELP)] = None,
    location: Annotated[str | None, typer.Option("--location", help="New location.")] = None,
    min_participants: Annotated[
        int | None, typer.Option("--min-participants", help="New minimum of participants.")
    ] = None,
    max_participants: Annotated[
        int | None, typer.Option("--max-participants", help="New maximum of participants.")
    ] = None,
    duration: Annotated[
        int | None, typer.Option("--duration", help="New duration in minutes.")
    ] = None,
) -> None:
    """Change one or more fields of one of your activities. Requires a session."""
    changes = ActivityChanges(
        name=name,
        price=price,
        date=date,
        location=location,
        min_participants=min_participants,
        max_participants=max_participants,
        duration=duration,
    )
    if changes.is_empty():
        raise typer.BadParameter("at least one field to update is required", param_hint="options")
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)
    with authorized_client(settings) as client, login_hint():
        updated = client.update_activity(activity_id, changes)
    _print_activity(updated, "updated")


@app.command("delete")
@handle_errors
def delete_activity(
    ctx: typer.Context,
    activity_id: Annotated[
        str, typer.Argument(metavar="ACTIVITY_ID", help="ID of the activity to delete.")
    ],
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Delete without asking for confirmation.")
    ] = False,
) -> None:
    """Delete one of your activities after confirmation. Requires a session."""
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)
    with authorized_client(settings) as client:
        if not yes and not typer.confirm(f"Delete activity {activity_id}?", default=False):
            console.print("Deletion cancelled.", markup=False, highlight=False)
            return
        with login_hint():
            client.delete_activity(activity_id)
    console.print(f"Activity {activity_id} deleted.", markup=False, highlight=False)


@app.command("status")
@handle_errors
def change_status(
    ctx: typer.Context,
    activity_id: Annotated[
        str, typer.Argument(metavar="ACTIVITY_ID", help="ID of the activity, e.g. activity-5.")
    ],
    new_status: Annotated[
        ActivityStatus, typer.Argument(metavar="NEW_STATUS", help="Status to move the activity to.")
    ],
    yes: Annotated[
        bool,
        typer.Option(
            "--yes", "-y", help="Move to done or cancelled without asking for confirmation."
        ),
    ] = False,
) -> None:
    """Change the status of one of your activities. Requires a session.

    The API decides the valid transitions. Moving to done or cancelled is final: it asks first.
    """
    activity_id = activity_id.strip()
    if not activity_id:
        raise typer.BadParameter("ACTIVITY_ID cannot be empty", param_hint="ACTIVITY_ID")
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)
    with authorized_client(settings) as client:
        if (
            new_status in FINAL_STATUSES
            and not yes
            and not typer.confirm(
                f"Change activity {activity_id} to {new_status.value}? This cannot be undone.",
                default=False,
            )
        ):
            console.print("Status change cancelled.", markup=False, highlight=False)
            return
        with login_hint():
            changed = client.change_activity_status(activity_id, new_status.value)
    _print_activity(changed, f"is now {changed.status}")


def _print_activity(activity: Activity, done: str) -> None:
    """Print `Activity <id> <done>.` and the activity as a table without header."""
    console.print(f"Activity {activity.id} {done}.", markup=False, highlight=False)
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column(style="bold", no_wrap=True)
    table.add_column(overflow="fold")
    table.add_row("ID", activity.id)
    table.add_row("Name", activity.name)
    table.add_row("Date", _format_date(activity.date))
    table.add_row("Location", activity.location)
    table.add_row("Price", _format_price(activity.price))
    table.add_row("Capacity", str(activity.max_participants))
    table.add_row("Status", activity.status)
    console.print(table, markup=False, highlight=False)


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
