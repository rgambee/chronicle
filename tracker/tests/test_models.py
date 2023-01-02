from django.test import TestCase
from django.utils import timezone

from tracker.models import Entry, Tag, get_empty_tag
from tracker.tests.utils import SAMPLE_DATE, TrackerTestCase


class TestTag(TestCase):
    def test_empty_tag(self) -> None:
        empty_tag = get_empty_tag()
        self.assertEqual(empty_tag.name, "")

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
        url = entry.get_absolute_url()
        self.assertRegex(url, r"^/entry/[0-9]+/$")


# These two tests are separate classes because they require the test database to be in
# different states.
class TestCommonTagsEmpty(TestCase):
    def test_categories(self) -> None:
        """For an empty DB, no tags should be returned"""
        self.assertQuerysetEqual(Tag.most_common_categories(), [])

    def test_tags(self) -> None:
        """For an empty DB, no tags should be returned"""
        self.assertQuerysetEqual(Tag.most_common_tags(), [])


class TestCommonTagsPopulated(TrackerTestCase):
    tags = [Tag("a"), Tag("b"), Tag("c"), Tag("")]
    entries = [
        Entry(amount=1.0, date=SAMPLE_DATE, category=tags[1]),
        Entry(amount=1.0, date=SAMPLE_DATE, category=tags[1]),
        Entry(amount=1.0, date=SAMPLE_DATE, category=tags[2]),
    ]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        # Tags need to be applied after entries have been saved
        cls.entries[0].tags.set([cls.tags[0], cls.tags[2]])
        cls.entries[2].tags.set([cls.tags[2]])

    def test_categories(self) -> None:
        """Rows should be returned in decreasing category frequency"""
        self.assertQuerysetEqual(
            Tag.most_common_categories(),
            [self.tags[1], self.tags[2], self.tags[0]],
        )

    def test_tags(self) -> None:
        """Rows should be returned in decreasing tag frequency"""
        self.assertQuerysetEqual(
            Tag.most_common_tags(),
            [self.tags[2], self.tags[0], self.tags[1]],
        )
