from datetime import UTC, datetime

import pytest

from activity_bookings.api_client import Activity
from activity_bookings.booking_rules import check_bookable
from activity_bookings.errors import ActivityBookingsError

NOW = datetime(2026, 12, 20, 23, 0, tzinfo=UTC)


def activity(status: str = "published", date: str = "2100-12-20T10:00:00.000Z") -> Activity:
    return Activity(
        id="activity-2",
        name="City Bike Tour",
        date=date,
        location="City Center",
        price=35.0,
        max_participants=15,
        status=status,
    )


@pytest.mark.parametrize("status", ["draft", "cancelled", "done", "sold-out", "confirmed"])
def test_status_not_published(status: str) -> None:
    with pytest.raises(ActivityBookingsError) as exc:
        check_bookable(activity(status=status), NOW)
    assert str(exc.value) == f"activity activity-2 is not open for booking (status: {status})"


def test_status_checked_before_date() -> None:
    with pytest.raises(ActivityBookingsError, match="not open for booking"):
        check_bookable(activity(status="draft", date="pronto"), NOW)


@pytest.mark.parametrize(
    "date",
    [
        "2100-12-20T10:00:00.000Z",  # future date-time
        "2026-12-20",  # today, without time
        "2026-12-21",  # tomorrow, without time
        "2026-12-20T23:30:00",  # later today, without zone (UTC)
    ],
)
def test_bookable(date: str) -> None:
    check_bookable(activity(date=date), NOW)


@pytest.mark.parametrize(
    ("date", "shown"),
    [
        ("2000-08-25T14:00:00.000Z", "2000-08-25 14:00 UTC"),
        ("2026-12-20T23:00:00.000Z", "2026-12-20 23:00 UTC"),  # exactly now
        ("2026-12-19", "2026-12-19"),  # yesterday, without time
        ("2026-12-20T22:59:00", "2026-12-20 22:59 UTC"),  # without zone, taken as UTC
        ("2026-12-21T00:30:00+02:00", "2026-12-20 22:30 UTC"),
    ],
)
def test_already_took_place(date: str, shown: str) -> None:
    with pytest.raises(ActivityBookingsError) as exc:
        check_bookable(activity(date=date), NOW)
    assert str(exc.value) == f"activity activity-2 already took place on {shown}"


def test_unreadable_date() -> None:
    with pytest.raises(ActivityBookingsError) as exc:
        check_bookable(activity(date="pronto"), NOW)
    assert str(exc.value) == "cannot read the date of activity activity-2: 'pronto'"
