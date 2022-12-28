from django.test import Client
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from tracker.tests.utils import TrackerTestCase


class TestEntryDetail(TrackerTestCase):
    def test_present(self) -> None:
        """Viewing an existing entry should return a successful response"""
        response = Client().get(reverse("entry", args=(1,)))
        self.assertEqual(response.status_code, 200)

    def test_absent(self) -> None:
        """Viewing a nonexistent entry should return a 404 response"""
        response = Client().get(reverse("entry", args=(99,)))
        self.assertEqual(response.status_code, 404)

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
        response = Client().get("entry//abc/")
        self.assertEqual(response.status_code, 404)
