import json
import logging
from datetime import datetime
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.test import Client
from django.urls import reverse
from django.utils.timezone import make_aware

from tracker.models import Entry, Tag
from tracker.tests.utils import TrackerTestCase, construct_entry_form
from tracker.view_utils import get_recent_entries, prepare_entries_for_serialization
from tracker.views import EntryCreate


class TestEntryUpdates(TrackerTestCase):
    def test_get(self) -> None:
        """A GET request should return a METHOD_NOT_ALLOWED error"""
        with self.assertLogs(level=logging.WARNING):
            response = Client().get(reverse("updates"))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(response.get("Allow"), "POST")

    def test_post_empty(self) -> None:
        """A POST request with not data should return a BAD_REQUEST error"""
        with self.assertLogs(level=logging.ERROR):
            response = Client().post(reverse("updates"))
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_post_valid(self) -> None:
        starting_entry_count = self.entry_count
        with self.assertLogs(level=logging.INFO):
            response = Client().post(
                reverse("updates"),
                data={"updates": json.dumps({"deletions": [1]})},
            )
        self.assertRedirects(response, reverse("entries"))
        self.assertEqual(self.entry_count, starting_entry_count - 1)


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

    @patch("tracker.view_utils.timezone.now")
    def test_recent_entries(self, now_mock: MagicMock) -> None:
        """Queryset should be limited according to specified time span"""
        now_mock.return_value = self.entries[0].date
        response = Client().get(reverse("entries-recent", args=(1, "months")))
        self.assertQuerysetEqual(
            response.context["entries"],
            self.entries[:2],
        )

    @patch("tracker.view_utils.timezone.now")
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


class TestListAndCreate(TrackerTestCase):
    def test_get(self) -> None:
        """A GET request should return a form and a list of existing entries"""
        response = Client().get(reverse("entries"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_list.html")

    def test_post(self) -> None:
        """A POST request with valid data should be accepted"""
        initial_count = self.entry_count
        form = construct_entry_form()
        self.assertTrue(form.is_valid())
        response = Client().post(reverse("entries"), data=form.data, follow=True)
        self.assertRedirects(response, reverse("entries"))
        self.assertContains(
            response,
            EntryCreate().get_success_message(form.cleaned_data),
            status_code=HTTPStatus.OK,
        )
        self.assertEqual(self.entry_count, initial_count + 1)


class TestChartView(TrackerTestCase):
    tags = (Tag("red"), Tag("blue"))
    entries = (
        Entry(amount=1.0, date=make_aware(datetime(2000, 3, 1)), category=tags[0]),
        Entry(amount=2.0, date=make_aware(datetime(2000, 2, 1)), category=tags[1]),
        Entry(amount=3.0, date=make_aware(datetime(2000, 1, 1)), category=tags[0]),
    )

    def test_get_all(self) -> None:
        """A general GET request should include all entries"""
        response = Client().get(reverse("charts"))
        self.assertTemplateUsed(response, "tracker/charts.html")
        self.assertEqual(
            response.context["entries"],
            prepare_entries_for_serialization(Entry.objects.all()),
        )

    @patch("tracker.view_utils.timezone.now")
    def test_get_recent(self, now_mock: MagicMock) -> None:
        """A GET request that specifies a time range should narrow the entries"""
        now_mock.return_value = self.entries[0].date
        response = Client().get(reverse("charts-recent", args=(1, "months")))
        self.assertTemplateUsed(response, "tracker/charts.html")
        self.assertEqual(
            response.context["entries"],
            prepare_entries_for_serialization(
                get_recent_entries(Entry.objects.all(), 1, "months")
            ),
        )
