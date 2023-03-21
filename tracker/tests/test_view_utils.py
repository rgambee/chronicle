import json
from datetime import datetime, timedelta, timezone
from typing import List, Sequence
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils.timezone import get_current_timezone, make_aware, override

from tracker.models import Entry, Tag
from tracker.tests.utils import TrackerTestCase
from tracker.view_utils import (
    SerializableEntry,
    aggregate_entries,
    format_datetime_ecma,
    get_recent_entries,
    prepare_entries_for_serialization,
    subtract_timedelta,
)


class TestRecentEntries(TrackerTestCase):
    tags = (Tag("t"),)
    entries = (
        Entry(amount=1.0, date=make_aware(datetime(2000, 3, 1)), category=tags[0]),
        Entry(amount=2.0, date=make_aware(datetime(2000, 3, 1)), category=tags[0]),
        Entry(amount=3.0, date=make_aware(datetime(2000, 2, 25)), category=tags[0]),
        Entry(amount=4.0, date=make_aware(datetime(2000, 2, 1)), category=tags[0]),
        Entry(amount=5.0, date=make_aware(datetime(2000, 1, 1)), category=tags[0]),
    )

    def test_all_entries(self) -> None:
        """If no optional arguments are given, all entries should be returned"""
        self.assertQuerysetEqual(
            get_recent_entries(Entry.objects.all()),
            self.entries,
        )

    def test_one_year(self) -> None:
        """Should return all entries within the previous year"""
        self.assertQuerysetEqual(
            get_recent_entries(
                queryset=Entry.objects.all(),
                amount=1,
                unit="years",
                end=make_aware(datetime(2000, 3, 1)),
            ),
            self.entries,
        )

    def test_one_month(self) -> None:
        """Should return all entries within the previous month"""
        self.assertQuerysetEqual(
            get_recent_entries(
                queryset=Entry.objects.all(),
                amount=1,
                unit="months",
                end=make_aware(datetime(2000, 3, 1)),
            ),
            self.entries[:-1],
        )

    def test_one_week(self) -> None:
        """Should return all entries within the previous week"""
        self.assertQuerysetEqual(
            get_recent_entries(
                queryset=Entry.objects.all(),
                amount=1,
                unit="weeks",
                end=make_aware(datetime(2000, 3, 1)),
            ),
            self.entries[:-2],
        )

    def test_one_day(self) -> None:
        """Should return all entries within the previous day"""
        self.assertQuerysetEqual(
            get_recent_entries(
                queryset=Entry.objects.all(),
                amount=1,
                unit="days",
                end=make_aware(datetime(2000, 3, 1)),
            ),
            self.entries[:-3],
        )

    def test_order(self) -> None:
        """Order of input queryset should be preserved"""
        self.assertQuerysetEqual(
            get_recent_entries(
                queryset=Entry.objects.order_by("-amount"),
                amount=1,
                unit="years",
                end=make_aware(datetime(2000, 3, 1)),
            ),
            self.entries[::-1],
        )

    @patch("tracker.view_utils.timezone.now")
    def test_default_end(self, now_mock: MagicMock) -> None:
        """End date should default to today"""
        now_mock.return_value = make_aware(datetime(2000, 2, 25))
        self.assertQuerysetEqual(
            get_recent_entries(
                queryset=Entry.objects.all(),
                amount=4,
                unit="weeks",
            ),
            self.entries[2:-1],
        )


class TestSubtractTimedelta(TestCase):
    def test_years(self) -> None:
        """Subtracting years should leave other fields untouched"""
        end = datetime(2000, 3, 21, 12, 34, 56)
        start = subtract_timedelta(end, 0, "years")
        self.assertEqual(start, end)
        start = subtract_timedelta(end, 1, "years")
        self.assertEqual(start, datetime(1999, 3, 21, 12, 34, 56))
        start = subtract_timedelta(end, 100, "years")
        self.assertEqual(start, datetime(1900, 3, 21, 12, 34, 56))

    def test_months(self) -> None:
        """Subtracting months should decrement year when appropriate"""
        end = datetime(2000, 3, 21, 12, 34, 56)
        start = subtract_timedelta(end, 0, "months")
        self.assertEqual(start, end)
        start = subtract_timedelta(end, 1, "months")
        self.assertEqual(start, datetime(2000, 2, 21, 12, 34, 56))
        start = subtract_timedelta(end, 3, "months")
        self.assertEqual(start, datetime(1999, 12, 21, 12, 34, 56))
        start = subtract_timedelta(end, 12, "months")
        self.assertEqual(start, datetime(1999, 3, 21, 12, 34, 56))

    def test_weeks(self) -> None:
        """Subtracting weeks should follow the expected rules"""
        end = datetime(2000, 3, 21, 12, 34, 56)
        start = subtract_timedelta(end, 0, "weeks")
        self.assertEqual(start, end)
        start = subtract_timedelta(end, 1, "weeks")
        self.assertEqual(start, datetime(2000, 3, 14, 12, 34, 56))
        start = subtract_timedelta(end, 3, "weeks")
        self.assertEqual(start, datetime(2000, 2, 29, 12, 34, 56))
        start = subtract_timedelta(end, 8, "weeks")
        self.assertEqual(start, datetime(2000, 1, 25, 12, 34, 56))

    def test_days(self) -> None:
        """Subtracting days should follow the expected rules"""
        end = datetime(2000, 3, 21, 12, 34, 56)
        start = subtract_timedelta(end, 0, "days")
        self.assertEqual(start, end)
        start = subtract_timedelta(end, 1, "days")
        self.assertEqual(start, datetime(2000, 3, 20, 12, 34, 56))
        start = subtract_timedelta(end, 21, "days")
        self.assertEqual(start, datetime(2000, 2, 29, 12, 34, 56))

    def test_negative_amount(self) -> None:
        """A negative amount should raise a ValueError"""
        end = datetime(2000, 3, 21, 12, 34, 56)
        with self.assertRaises(ValueError):
            subtract_timedelta(end, -1, "days")

    def test_unrecognized_unit(self) -> None:
        """Unrecognized units should raise a TypeError

        A ValueError feels more appropriate to me, but the datetime.timedelta() raises a
        TypeError in this situation.
        """
        end = datetime(2000, 3, 21, 12, 34, 56)
        with self.assertRaises(TypeError):
            subtract_timedelta(end, 1, "fortnights")

    def test_day_out_of_range(self) -> None:
        """Invalid dates (like February 30th) should shift forward to next valid one"""
        end = datetime(2000, 3, 31, 12, 34, 56)
        start = subtract_timedelta(end, 1, "months")
        self.assertEqual(start, end.replace(day=1))
        start = subtract_timedelta(end, 2, "months")
        self.assertEqual(start, end.replace(month=1))
        start = subtract_timedelta(end, 3, "months")
        self.assertEqual(start, datetime(1999, 12, 31, 12, 34, 56))
        start = subtract_timedelta(end, 4, "months")
        self.assertEqual(start, datetime(1999, 12, 1, 12, 34, 56))
        # Test subtracting from a leap year
        end = datetime(2000, 2, 29, 12, 34, 56)
        start = subtract_timedelta(end, 1, "years")
        self.assertEqual(start, datetime(1999, 3, 1, 12, 34, 56))


class TestEntrySerialization(TrackerTestCase):
    def check_json_serialization(
        self,
        serializable: Sequence[SerializableEntry],
    ) -> None:
        """Check that SerializableEntries can be JSON-(de)serialized losslessly"""
        serialized = json.dumps(serializable)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized, serializable)

    def test_empty_queryset(self) -> None:
        """An empty queryset should yield an empty list"""
        entries: List[Entry] = []
        serializable = prepare_entries_for_serialization(entries)
        self.assertEqual(serializable, [])
        self.check_json_serialization(serializable)

    def test_nonempty_queryset(self) -> None:
        """A nonempty queryset should be converted with order preserved"""
        entries = Entry.objects.all()
        self.assertGreater(len(entries), 0)
        serializable = prepare_entries_for_serialization(entries)
        self.assertEqual(len(serializable), len(entries))
        self.check_json_serialization(serializable)


class TestEntryAggregation(TrackerTestCase):
    timezone_for_testing = timezone.utc
    tags = (Tag("red"), Tag("blue"))
    entries = (
        Entry(
            amount=1.0,
            date=datetime(2000, 3, 1, tzinfo=timezone_for_testing),
            category=tags[0],
        ),
        Entry(
            amount=2.0,
            date=datetime(2000, 2, 1, tzinfo=timezone_for_testing),
            category=tags[1],
        ),
        Entry(
            amount=3.0,
            date=datetime(2000, 1, 1, tzinfo=timezone_for_testing),
            category=tags[0],
        ),
    )

    def test_empty_queryset(self) -> None:
        """An empty queryset should yield an empty dict"""
        self.assertEqual(aggregate_entries(Entry.objects.none()), {})

    @override(timezone_for_testing)
    def test_one_category(self) -> None:
        """One category should yield a dict with one item"""
        aggregated = aggregate_entries(Entry.objects.filter(category_id=self.tags[0]))
        self.assertEqual(
            aggregated,
            {
                self.tags[0].name: {
                    format_datetime_ecma(self.entries[0].date): self.entries[0].amount,
                    format_datetime_ecma(self.entries[2].date): self.entries[2].amount,
                },
            },
        )

        aggregated = aggregate_entries(Entry.objects.filter(category_id=self.tags[1]))
        self.assertEqual(
            aggregated,
            {
                self.tags[1].name: {
                    format_datetime_ecma(self.entries[1].date): self.entries[1].amount,
                },
            },
        )

    @override(timezone_for_testing)
    def test_multiple_categories(self) -> None:
        """Multiple categories should yield a dict with multiple items"""
        aggregated = aggregate_entries(Entry.objects.all())
        self.assertEqual(
            aggregated,
            {
                self.tags[0].name: {
                    format_datetime_ecma(self.entries[0].date): self.entries[0].amount,
                    format_datetime_ecma(self.entries[2].date): self.entries[2].amount,
                },
                self.tags[1].name: {
                    format_datetime_ecma(self.entries[1].date): self.entries[1].amount,
                },
            },
        )

    @override(timezone_for_testing)
    def test_prefiltered_queryset(self) -> None:
        """Aggregation only include entries in the given queryset"""
        queryset = Entry.objects.filter(category_id=self.tags[0], amount__gte=2.0)
        aggregated = aggregate_entries(queryset)
        self.assertEqual(
            aggregated,
            {
                self.tags[0].name: {
                    format_datetime_ecma(self.entries[2].date): self.entries[2].amount,
                },
            },
        )

    def test_timezone(self) -> None:
        """Dates should be converted to current timezone before aggregation"""
        queryset = Entry.objects.filter(category_id=self.tags[1])

        for offset_hours in (-23, -1, 0, 1, 23):
            with override(timezone(timedelta(hours=offset_hours))):
                with self.subTest(timezone=get_current_timezone()):
                    aggregated = aggregate_entries(queryset)
                    expected_datetime = format_datetime_ecma(
                        # pylint thinks Entry.date has type DateTimeField, when the
                        # actual type is datetime, making it complain about using the
                        # astimezone() method. This is understandable since Django is
                        # overriding the class attribute with the instance attribute.
                        # pylint: disable-next=no-member
                        self.entries[1]
                        .date.astimezone(get_current_timezone())
                        .replace(hour=0, minute=0, second=0, microsecond=0)
                    )
                    self.assertEqual(
                        aggregated,
                        {
                            self.tags[1].name: {
                                expected_datetime: self.entries[1].amount,
                            },
                        },
                    )


class TestDatetimeFormat(TestCase):
    def test_format(self) -> None:
        """Datetimes should be converted to ISO-8601 format with timezone info"""
        sample_dt = datetime(
            year=2000,
            month=1,
            day=2,
            hour=12,
            minute=34,
            second=56,
            microsecond=987654,
            tzinfo=timezone(timedelta(hours=12, minutes=34)),
        )
        self.assertEqual(
            format_datetime_ecma(sample_dt),
            "2000-01-02T12:34:56.987+12:34",
        )
