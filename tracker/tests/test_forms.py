from typing import Any, Optional, Sequence

from tracker.forms import EntryForm
from tracker.models import Entry, Tag
from tracker.tests.utils import SAMPLE_DATE, TrackerTestCase, construct_entry_form


class TestFormValidation(TrackerTestCase):
    tags = [Tag("category1"), Tag("tag1"), Tag("tag2")]
    entries = []

    @classmethod
    def construct_entry_form(
        cls,
        *,
        category: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> EntryForm:
        """Create a form with the given fields and assert that it's valid"""
        if category is None:
            category = cls.tags[0].name
        if tags is None:
            tags = [tag.name for tag in cls.tags[1:]]
        return construct_entry_form(category=category, tags=tags, **kwargs)

    def good(self, **kwargs: Any) -> None:
        """Create a form with the given fields and assert that it's valid"""
        form = self.construct_entry_form(**kwargs)
        self.assertEqual(form.errors, {})

    def bad(self, *, field: str, message: str, **kwargs: Any) -> None:
        """Create a form with the given fields and assert the given field is invalid"""
        form = self.construct_entry_form(**kwargs)
        self.assertTrue(form.has_error(field))
        self.assertEqual(form.errors, {field: [message]})

    def test_default(self) -> None:
        """Check that the default form is valid"""
        form = construct_entry_form()
        self.assertEqual(form.errors, {})

    def test_amount_field(self) -> None:
        """Check that amounts are validated correctly"""
        self.good(amount=1.0)
        self.good(amount=0.0)
        self.good(amount="1.0")
        self.bad(
            amount=-1.0,
            field="amount",
            message="Ensure this value is greater than or equal to 0.0.",
        )
        self.bad(amount="a", field="amount", message="Enter a number.")
        self.bad(category="", field="category", message="This field is required.")

    def test_date_field(self) -> None:
        """Check that dates are validated correctly"""
        self.good(date="2001-02-03")
        self.good(date="1/23/2004")
        self.good(date="1 Feb 2003")
        invalid = "Enter a valid date/time."
        self.bad(date="Jan 32 2001", field="date", message=invalid)
        self.bad(date="yesterday", field="date", message=invalid)
        self.bad(date="November 1", field="date", message=invalid)
        self.bad(category="", field="category", message="This field is required.")

    def test_category_field(self) -> None:
        """Check that categories are validated correctly"""
        self.good(category="category1")
        self.bad(
            category="category2",
            field="category",
            message=(
                "Select a valid choice. "
                "That choice is not one of the available choices."
            ),
        )
        self.bad(category="", field="category", message="This field is required.")

    def test_tags_field(self) -> None:
        """Check that tags are validated correctly"""
        self.good(tags=["tag1"])
        self.good(tags=["tag2"])
        self.good(tags=["tag1", "tag2"])
        self.good(tags=[])
        unrecognized = "Select a valid choice. {} is not one of the available choices."
        self.bad(tags=["tag3"], field="tags", message=unrecognized.format("tag3"))
        self.bad(
            tags=["tag1", "tag3"], field="tags", message=unrecognized.format("tag3")
        )
        self.bad(tags=[1], field="tags", message=unrecognized.format(1))

    def test_comment_field(self) -> None:
        """Check that comments are validated correctly"""
        self.good(comment="")
        self.good(comment="This comment is false.")
        self.good(comment=1)


class TestFormChoices(TrackerTestCase):
    tags = [Tag("red"), Tag("green"), Tag("blue")]
    entries = [
        Entry(amount=1.0, date=SAMPLE_DATE, category=Tag("red")),
        Entry(amount=1.0, date=SAMPLE_DATE, category=Tag("red")),
        Entry(amount=1.0, date=SAMPLE_DATE, category=Tag("green")),
    ]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.entries[0].tags.set(cls.tags[1:])
        cls.entries[1].tags.set(cls.tags[2:])

    def test_category_order(self) -> None:
        """Category choices should be in descending order of prevalence"""
        form = EntryForm()
        category_queryset = form.fields[
            "category"
        ].queryset  # type: ignore[attr-defined]
        self.assertQuerysetEqual(
            category_queryset,
            [Tag("red"), Tag("green"), Tag("blue")],
        )

    def test_tags_order(self) -> None:
        """Tag choices should be in descending order of prevalence"""
        form = EntryForm()
        tags_queryset = form.fields["tags"].queryset  # type: ignore[attr-defined]
        self.assertQuerysetEqual(
            tags_queryset,
            [Tag("blue"), Tag("green"), Tag("red")],
        )
