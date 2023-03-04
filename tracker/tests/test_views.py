import logging
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.timezone import get_current_timezone, make_aware, override

from tracker.models import Entry, Tag
from tracker.tests.utils import TrackerTestCase, construct_entry_form
from tracker.views import (
    EntryCreate,
    EntryDelete,
    EntryEdit,
    aggregate_entries,
    format_datetime_ecma,
    get_recent_entries,
    subtract_timedelta,
)


class TestEntryDetail(TrackerTestCase):
    def test_present(self) -> None:
        """Viewing an existing entry should return a successful response"""
        response = Client().get(reverse("entry", args=(self.entry_count,)))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_detail.html")

    def test_absent(self) -> None:
        """Viewing a nonexistent entry should return a 404 response"""
        with self.assertLogs(level=logging.WARNING):
            response = Client().get(reverse("entry", args=(self.entry_count + 1,)))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateNotUsed(response, "tracker/entry_detail.html")

    def test_invalid_reverse(self) -> None:
        """Attempting to reverse an invalid entries should raise an error"""
        with self.assertRaises(NoReverseMatch):
            reverse("entry", args=("abc",))

    def test_invalid_get(self) -> None:
        """If an invalid entry is somehow accessed, is should return a 404"""
        # Client.get() strips interior slashes:
        #   entry/abc  -> entryabc
        #   entry//abc -> entry/abc
        # The latter has a higher chance of matching a URL pattern, so it's the better
        # one to test.
        with self.assertLogs(level=logging.WARNING):
            response = Client().get("entry//abc/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateNotUsed(response, "tracker/entry_detail.html")


class TestEntryList(TrackerTestCase):
    tags = (Tag("red"), Tag("blue"))
    entries = (
        Entry(amount=1.0, date=make_aware(datetime(2000, 3, 1)), category=tags[0]),
        Entry(amount=2.0, date=make_aware(datetime(2000, 2, 1)), category=tags[1]),
        Entry(amount=3.0, date=make_aware(datetime(2000, 1, 1)), category=tags[0]),
    )

    def test_all_entries(self) -> None:
        """By default, the EntryListView should show all entries"""
        response = Client().get(reverse("entries"))
        self.assertQuerysetEqual(response.context["entries"], self.entries)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_list.html")

    def test_entries_in_category(self) -> None:
        """When examining a specific tag, only matching entries should be shown"""
        for tag in self.tags:
            with self.subTest(tag=tag.name):
                response = Client().get(
                    reverse("entries-in-category", args=(tag.name,))
                )
                self.assertQuerysetEqual(
                    response.context["entries"],
                    [ent for ent in self.entries if ent.category == tag],
                )
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertTemplateUsed(response, "tracker/entry_list.html")

    def test_empty_category(self) -> None:
        """When examining a nonexistent tag, no entries should be shown"""
        response = Client().get(reverse("entries-in-category", args=("other",)))
        self.assertQuerysetEqual(response.context["entries"], [])
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_list.html")

    @patch("tracker.views.timezone.now")
    def test_recent_entries(self, now_mock: MagicMock) -> None:
        """Queryset should be limited according to specified time span"""
        now_mock.return_value = self.entries[0].date
        response = Client().get(reverse("entries-recent", args=(1, "months")))
        self.assertQuerysetEqual(
            response.context["entries"],
            self.entries[:2],
        )

    @patch("tracker.views.timezone.now")
    def test_recent_in_category(self, now_mock: MagicMock) -> None:
        """Queryset should be limited to time span and category"""
        now_mock.return_value = self.entries[0].date
        response = Client().get(
            reverse("recent-in-category", args=(self.tags[0].name, 1, "months"))
        )
        self.assertQuerysetEqual(
            response.context["entries"],
            self.entries[:1],
        )


class TestEntryEdit(TrackerTestCase):
    tags = [Tag("tag1")]

    def test_get(self) -> None:
        """A GET request should return a form"""
        response = Client().get(reverse("edit", args=(self.entry_count,)))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_form.html")

    def test_post_valid(self) -> None:
        """A POST request with valid data should be accepted"""
        form = construct_entry_form()
        self.assertTrue(form.is_valid())
        response = Client().post(
            reverse("edit", args=(self.entry_count,)), data=form.data, follow=True
        )
        self.assertRedirects(response, reverse("entry", args=(self.entry_count,)))
        self.assertContains(
            response,
            EntryEdit().get_success_message(form.cleaned_data),
            status_code=HTTPStatus.OK,
        )

    def test_post_invalid(self) -> None:
        """A POST request with invalid data should be returned for edits"""
        form = construct_entry_form(category="")
        response = Client().post(
            reverse("edit", args=(self.entry_count,)), data=form.data
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_form.html")

    def test_post_nonexistent(self) -> None:
        """Trying to edit a nonexistent entry should return a 404"""
        with self.assertLogs(level=logging.WARNING):
            response = Client().get(reverse("edit", args=(self.entry_count + 1,)))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateNotUsed(response, "tracker/entry_form.html")


class TestListAndCreate(TrackerTestCase):
    def test_get(self) -> None:
        """A GET request should return a form and a list of existing entries"""
        response = Client().get(reverse("entries"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_list.html")

    def test_post(self) -> None:
        """A POST request with valid data should be accepted"""
        initial_count = Entry.objects.count()
        form = construct_entry_form()
        self.assertTrue(form.is_valid())
        response = Client().post(reverse("entries"), data=form.data, follow=True)
        self.assertRedirects(response, reverse("entries"))
        self.assertContains(
            response,
            EntryCreate().get_success_message(form.cleaned_data),
            status_code=HTTPStatus.OK,
        )
        self.assertEqual(Entry.objects.count(), initial_count + 1)


class TestEntryDelete(TrackerTestCase):
    def test_get(self) -> None:
        """A GET request should ask for confirmation"""
        response = Client().get(reverse("delete", args=(self.entry_count,)))
        self.assertTemplateUsed(response, "tracker/entry_confirm_delete.html")
        self.assertContains(response, "</form>")

    def test_get_nonexistent(self) -> None:
        """A GET request for a nonexistent entry should return a 404"""
        with self.assertLogs(level=logging.WARNING):
            response = Client().get(reverse("delete", args=(self.entry_count + 1,)))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateNotUsed(response, "tracker/entry_confirm_delete.html")

    def test_post(self) -> None:
        """A POST request should delete the corresponding object"""
        initial_count = Entry.objects.count()
        response = Client().post(
            reverse("delete", args=(self.entry_count,)), follow=True
        )
        self.assertRedirects(response, reverse("entries"))
        self.assertContains(
            response,
            EntryDelete.success_message,
            status_code=HTTPStatus.OK,
        )
        self.assertEqual(Entry.objects.count(), initial_count - 1)

    def test_post_nonexistent(self) -> None:
        """A POST request for a nonexistent entry should return a 404"""
        with self.assertLogs(level=logging.WARNING):
            response = Client().post(
                reverse("delete", args=(self.entry_count + 1,)), follow=True
            )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class TestChartView(TrackerTestCase):
    tags = (Tag("red"), Tag("blue"))
    entries = (
        Entry(amount=1.0, date=make_aware(datetime(2000, 3, 1)), category=tags[0]),
        Entry(amount=2.0, date=make_aware(datetime(2000, 2, 1)), category=tags[1]),
        Entry(amount=3.0, date=make_aware(datetime(2000, 1, 1)), category=tags[0]),
    )

    def test_get_all(self) -> None:
        """A general GET request should aggregate all entries"""
        response = Client().get(reverse("charts"))
        self.assertTemplateUsed(response, "tracker/charts.html")
        self.assertEqual(
            response.context["entries"],
            aggregate_entries(Entry.objects.all()),
        )

    @patch("tracker.views.timezone.now")
    def test_get_recent(self, now_mock: MagicMock) -> None:
        """A GET request that specifies a time range should narrow the entries"""
        now_mock.return_value = self.entries[0].date
        response = Client().get(reverse("charts-recent", args=(1, "months")))
        self.assertTemplateUsed(response, "tracker/charts.html")
        self.assertEqual(
            response.context["entries"],
            aggregate_entries(get_recent_entries(Entry.objects.all(), 1, "months")),
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

    @patch("tracker.views.timezone.now")
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
