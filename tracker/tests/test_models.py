from django.test import TestCase
from django.utils import timezone

from tracker.models import Entry, Tag


class TestTag(TestCase):
    def test_str(self) -> None:
        """Short representation of Tag should be its name"""
        tag_name = "mytag"
        tag = Tag(tag_name)
        self.assertEqual(str(tag), tag_name)

        tag = Tag("")
        self.assertEqual(str(tag), "<unset>")

    def test_repr(self) -> None:
        """Long representation of Tag should show class and name"""
        tag_name = "mytag"
        tag = Tag(tag_name)
        self.assertEqual(repr(tag), f"Tag({tag_name})")

        tag = Tag("")
        self.assertEqual(repr(tag), "Tag()")


class TestEntry(TestCase):
    SAMPLE_DATE = timezone.make_aware(timezone.datetime(2001, 1, 23))

    def test_str(self) -> None:
        """Short representation of Entry should show date and amount"""
        entry = Entry(date=TestEntry.SAMPLE_DATE, amount=1.23)
        self.assertEqual(str(entry), "Entry(date=2001-01-23, amount=1)")

    def test_repr(self) -> None:
        """Long representation of Entry should show more fields"""
        category = Tag("things")
        category.save()
        entry = Entry(date=TestEntry.SAMPLE_DATE, amount=1.23, category=category)
        self.assertEqual(
            repr(entry), "Entry(date=2001-01-23, amount=1, category=things, tags=[])"
        )
        entry.save()
        entry.tags.create(name="that")
        entry.tags.create(name="this")
        self.assertEqual(
            repr(entry),
            "Entry(date=2001-01-23, amount=1, category=things, tags=[that, this])",
        )
