import logging
from http import HTTPStatus

from django.test import Client
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from tracker.models import Entry, Tag
from tracker.tests.utils import SAMPLE_DATE, TrackerTestCase, construct_entry_form
from tracker.views import EntryCreate, EntryDelete, EntryEdit


class TestEntryDetail(TrackerTestCase):
    def test_present(self) -> None:
        """Viewing an existing entry should return a successful response"""
        response = Client().get(reverse("entry", args=(1,)))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_detail.html")

    def test_absent(self) -> None:
        """Viewing a nonexistent entry should return a 404 response"""
        with self.assertLogs(level=logging.WARNING):
            response = Client().get(reverse("entry", args=(99,)))
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
        Entry(amount=1.0, date=SAMPLE_DATE, category=tags[0]),
        Entry(amount=2.0, date=SAMPLE_DATE, category=tags[1]),
        Entry(amount=3.0, date=SAMPLE_DATE, category=tags[0]),
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


class TestEntryEdit(TrackerTestCase):
    tags = [Tag("tag1")]

    def test_get(self) -> None:
        """A GET request should return a form"""
        response = Client().get(reverse("edit", args=(1,)))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_form.html")

    def test_post_valid(self) -> None:
        """A POST request with valid data should be accepted"""
        form = construct_entry_form()
        self.assertTrue(form.is_valid())
        response = Client().post(
            reverse("edit", args=(1,)), data=form.data, follow=True
        )
        self.assertRedirects(response, reverse("entry", args=(1,)))
        self.assertContains(
            response,
            EntryEdit().get_success_message(form.cleaned_data),
            status_code=HTTPStatus.OK,
        )

    def test_post_invalid(self) -> None:
        """A POST request with invalid data should be returned for edits"""
        form = construct_entry_form(category="")
        response = Client().post(reverse("edit", args=(1,)), data=form.data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tracker/entry_form.html")

    def test_post_nonexistent(self) -> None:
        """Trying to edit a nonexistent entry should return a 404"""
        with self.assertLogs(level=logging.WARNING):
            response = Client().get(reverse("edit", args=(99,)))
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
        response = Client().get(reverse("delete", args=(1,)))
        self.assertTemplateUsed(response, "tracker/entry_confirm_delete.html")
        self.assertContains(response, "</form>")

    def test_get_nonexistent(self) -> None:
        """A GET request for a nonexistent entry should return a 404"""
        with self.assertLogs(level=logging.WARNING):
            response = Client().get(reverse("delete", args=(99,)))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateNotUsed(response, "tracker/entry_confirm_delete.html")

    def test_post(self) -> None:
        """A POST request should delete the corresponding object"""
        initial_count = Entry.objects.count()
        response = Client().post(reverse("delete", args=(1,)), follow=True)
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
            response = Client().post(reverse("delete", args=(99,)), follow=True)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
