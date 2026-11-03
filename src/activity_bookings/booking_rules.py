"""Client-side checks before booking: the API does not check an activity's state or date."""

from datetime import UTC, date, datetime

from activity_bookings.api_client import Activity
from activity_bookings.commands.activities_cmd import _format_date
from activity_bookings.errors import ActivityBookingsError

BOOKABLE_STATUS = "published"


def check_bookable(activity: Activity, now: datetime) -> None:
    """Raise ActivityBookingsError unless `activity` is published and has not taken place.

    A date without time stays bookable for the whole of that day (UTC). A date-time without zone
    is taken as UTC. `now` must be timezone-aware.
    """
    if activity.status != BOOKABLE_STATUS:
        raise ActivityBookingsError(
            f"activity {activity.id} is not open for booking (status: {activity.status})"
        )
    if _has_passed(activity, now):
        raise ActivityBookingsError(
            f"activity {activity.id} already took place on {_format_date(activity.date)}"
        )


def _has_passed(activity: Activity, now: datetime) -> bool:
    try:
        return date.fromisoformat(activity.date) < now.astimezone(UTC).date()
    except ValueError:
        pass
    try:
        moment = datetime.fromisoformat(activity.date)
    except ValueError:
        raise ActivityBookingsError(
            f"cannot read the date of activity {activity.id}: {activity.date!r}"
        ) from None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment <= now
