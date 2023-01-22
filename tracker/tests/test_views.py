import logging
from datetime import datetime
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.timezone import make_aware

from tracker.models import Entry, Tag
from tracker.tests.utils import TrackerTestCase, construct_entry_form
from tracker.views import EntryCreate, EntryDelete, EntryEdit, subtract_timedelta


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
