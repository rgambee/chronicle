import logging
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, TypedDict

from django.db.models.query import QuerySet
from django.http import Http404
from django.utils import timezone

from tracker.models import Entry


class SerializableEntry(TypedDict):
    """Selected Entry data in a form that's easily JSON-serializable"""

    # Datetimes are converted to Unix timestamps in milliseconds (not seconds) for
    # convenience when interfacing with JavaScript.
    timestamp_ms: int
    amount: float
    category: str


def get_recent_entries(
    queryset: QuerySet[Entry],
    amount: Optional[int] = None,
    unit: Optional[str] = None,
    end: Optional[datetime] = None,
) -> QuerySet[Entry]:
    """Filter the given queryset to only contain recent entries

    See the documentation for subtract_timedelta() for the requirements regarding the
    `amount` and `unit` arguments.

    `end` defaults to now.
    """
    logger = logging.getLogger(__name__)
    if amount is not None and unit is not None:
        if end is None:
            end = timezone.now()
        try:
            start = subtract_timedelta(end, amount, unit)
        except (TypeError, ValueError) as err:
            raise Http404("Invalid date range") from err
        queryset = queryset.filter(date__gte=start).filter(date__lte=end)
    elif amount is not None or unit is not None:
        logger.error("Invalid arguments: amount=%s, unit=%s", amount, unit)
        raise TypeError("Must provide both amount and unit or neither")
    return queryset


def subtract_timedelta(end: datetime, amount: int, unit: str) -> datetime:
    """Subtract the given amount of time from an end date

    `amount` must be a non-negative integer.

    `unit` may be one of the following:
        "years"
        "months"
        "weeks"
        "days"
        "hours"
        "minutes"
        "seconds"
    """
    # Time spans of weeks through seconds are well-defined, and we can rely on the
    # datetime library for the arithmetic. But years and months don't have fixed
    # durations, so they require some extra logic. In this case, we want to decrement
    # the year/month since that's what a person usually means by "one year/month ago".
    if amount < 0:
        raise ValueError("Time delta amount may not be negative")
    if unit == "years":
        year = end.year - amount
        start = datetime_replace(end, year=year)
    elif unit == "months":
        month = (end.month - amount - 1) % 12 + 1
        year = end.year + (end.month - amount - 1) // 12
        start = datetime_replace(end, year=year, month=month)
    else:
        delta = timedelta(**{unit: amount})
        start = end - delta
    return start


def datetime_replace(when: datetime, **kwargs: int) -> datetime:
    """Replace fields of a datetime, rolling forward to avoid invalid dates"""
    try:
        # mypy complains that we might try to set the tzinfo field to an int, which
        # would be a problem and is technically possible given signature of this
        # function. Admittedly, the signature is incorrect (kwargs elements can have
        # type int or Optional[tzinfo]), but annotating it correctly would be verbose
        # and less clear.
        result = when.replace(**kwargs)  # type: ignore[arg-type]
    except ValueError as err:
        if str(err) == "day is out of range for month":
            # Round invalid dates (like February 30th) forward to next valid one
            year = kwargs.get("year", when.year)
            month = kwargs.get("month", when.month)
            year += month // 12
            month = month % 12 + 1
            kwargs.pop("year", None)
            kwargs.pop("month", None)
            kwargs.pop("day", None)
            result = when.replace(
                year=year, month=month, day=1, **kwargs  # type: ignore[arg-type]
            )
        else:
            raise
    return result


def prepare_entries_for_serialization(
    entries: Iterable[Entry],
) -> List[SerializableEntry]:
    """Transform entries for easy JSON-serialization"""
    serializable_entries = []
    for entry in entries:
        serializable_entries.append(
            SerializableEntry(
                timestamp_ms=round(1000 * entry.date.timestamp()),
                amount=entry.amount,
                category=entry.category.name,
            )
        )
    return serializable_entries
