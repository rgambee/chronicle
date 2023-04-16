import logging
import unittest
from typing import Any, Optional, Sequence

from django.test import Client
from django.urls import reverse

from tracker.forms import (
    AutocompleteWidget,
    CreateEntryForm,
    EditEntryForm,
    GetOrCreateChoiceField,
    GetOrCreateMultipleChoiceField,
)
from tracker.models import Entry, Tag
from tracker.tests.utils import SAMPLE_DATE, TrackerTestCase, construct_entry_form


class TestAutocompleteWidget(TrackerTestCase):
    tags = [Tag("category1"), Tag("category2"), Tag("category3")]
    entries = []

    @unittest.skip("Temporarily skip while transitioning away from this widget")
    def test_render(self) -> None:
        """Test that the AutocompleteWidget renders to HTML as expected"""
        response = Client().get(reverse("entries"))
        self.assertTemplateUsed(response, AutocompleteWidget.template_name)
        self.assertTemplateUsed(response, AutocompleteWidget.option_template_name)
        expected_html = """
        <input
            type="text"
            id="id_category"
            class="form-control"
            name="category"
            value="category1"
            list="id_category_list"
            spellcheck="true"
            required=""
        >

        <datalist id="id_category_list">
            <option value="category1">category1</option>
            <option value="category2">category2</option>
            <option value="category3">category3</option>
        </datalist>
        """
        self.assertContains(response, expected_html, html=True)

    def test_format_value(self) -> None:
        """Test that the AutocompleteWidget formats the selected value as a string"""
        widget = AutocompleteWidget()
        self.assertEqual(widget.format_value("abc"), "abc")
        self.assertEqual(widget.format_value(["abc"]), "abc")
        self.assertEqual(widget.format_value(None), "")
        self.assertEqual(widget.format_value([None]), "")
        self.assertEqual(widget.format_value(Tag("mytag")), "mytag")
        with self.assertLogs(level=logging.WARNING):
            self.assertEqual(widget.format_value([]), "")
        with self.assertLogs(level=logging.WARNING):
            self.assertEqual(widget.format_value([1, 2, 3]), "1")


class TestGetOrCreateChoiceField(TrackerTestCase):
    tags = [Tag("category1"), Tag("category2"), Tag("category3")]
    entries = []

    def test_queryset_none(self) -> None:
        """Test that a queryset of None raises a TypeError"""
        field = GetOrCreateChoiceField(queryset=None)
        with self.assertRaises(TypeError):
            field.to_python("any_tag")

    def test_empty_value(self) -> None:
        """Test that various empty values are converted to None"""
        field = GetOrCreateChoiceField(queryset=Tag.objects)
        self.assertIsNone(field.to_python(""))
        self.assertIsNone(field.to_python([]))
        self.assertIsNone(field.to_python(None))

    def test_get_existing(self) -> None:
        """Test an existing category is selected without adding new ones"""
        existing_tags = Tag.objects
        field = GetOrCreateChoiceField(queryset=existing_tags)
        self.assertEqual(field.to_python(self.tags[0].name), self.tags[0])
        self.assertQuerysetEqual(existing_tags.all(), self.tags, ordered=False)

    def test_create(self) -> None:
        """Test that a new category is created as needed"""
        existing_tags = Tag.objects
        new_tag = Tag("new")
        field = GetOrCreateChoiceField(queryset=existing_tags)
        self.assertEqual(field.to_python(new_tag.name), new_tag)
        self.assertQuerysetEqual(
            existing_tags.all(), self.tags + [new_tag], ordered=False
        )


class TestGetOrCreateMultipleChoiceField(TrackerTestCase):
    tags = [Tag("tag1"), Tag("tag2"), Tag("tag3")]
    entries = []

    def test_queryset_none(self) -> None:
        """Test that a queryset of None raises a TypeError"""
        field = GetOrCreateMultipleChoiceField(queryset=None)
        with self.assertRaises(TypeError):
            # pylint: disable-next=protected-access
            field._check_values([])

    def test_get_existing(self) -> None:
        """Test that existing tags are selected without adding new ones"""
        existing_tags = Tag.objects
        field = GetOrCreateMultipleChoiceField(queryset=existing_tags)
        selected_tags = [self.tags[0], self.tags[2]]
        self.assertQuerysetEqual(
            # pylint: disable-next=protected-access
            field._check_values(selected_tags),
            selected_tags,
            ordered=False,
        )
        self.assertQuerysetEqual(existing_tags.all(), self.tags, ordered=False)

    def test_create(self) -> None:
        """Test that new tags are created as needed"""
        existing_tags = Tag.objects
        field = GetOrCreateMultipleChoiceField(queryset=existing_tags)
        new_tags = [Tag("newA"), Tag("newB")]
        selected_tags = [self.tags[1]] + new_tags
        self.assertQuerysetEqual(
            # pylint: disable-next=protected-access
            field._check_values(selected_tags),
            selected_tags,
            ordered=False,
        )
        self.assertQuerysetEqual(
            existing_tags.all(), self.tags + new_tags, ordered=False
        )


class TestCreateEntryFormValidation(TrackerTestCase):
    tags = [Tag("category1"), Tag("tag1"), Tag("tag2")]
    entries = []

    @classmethod
    def construct_entry_form(
        cls,
        *,
        category: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> CreateEntryForm:
        """Create a form with the given fields"""
        if category is None:
            category = cls.tags[0].name
        if tags is None:
            tags = [tag.name for tag in cls.tags[1:]]
        return construct_entry_form(category=category, tags=tags, **kwargs)

    def good(self, **kwargs: Any) -> None:
        """Create a form with the given fields and assert that it's valid"""
        form = self.construct_entry_form(**kwargs)
        # mypy requires the first argument to assertFormError be an instance of
        # django.forms.Form. tracker.forms.CreateEntryForm is a subclass of
        # django.forms.BaseForm but not Form itself. It's possible the type stub for
        # this function should be edited to accept BaseForms. For now, the
        # `# type: ignore` comment silences the error.
        self.assertFormError(form, field=None, errors=[])  # type: ignore[call-overload]

    def bad(self, *, field: str, message: str, **kwargs: Any) -> None:
        """Create a form with the given fields and assert the given field is invalid"""
        form = self.construct_entry_form(**kwargs)
        self.assertFormError(form, field, errors=message)  # type: ignore[call-overload]

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
        # Existing category is ok
        self.good(category="category1")
        # New category is ok
        self.good(category="category2")
        # Missing category is not ok
        self.bad(category="", field="category", message="This field is required.")

    def test_tags_field(self) -> None:
        """Check that tags are validated correctly"""
        # Existing tags are ok
        self.good(tags=["tag1"])
        self.good(tags=["tag2"])
        # Multiple tags are ok
        self.good(tags=["tag1", "tag2"])
        # 0 tags are ok
        self.good(tags=[])
        # New tags are ok
        self.good(tags=["tag3"])
        self.good(tags=["tag5", "tag6"])
        # Mix of new and existing tags is ok
        self.good(tags=["tag1", "tag4"])
        # Anything that can be converted to a string is ok
        self.good(tags=[1])
        # Nested tags are not ok
        self.bad(tags=[["tag1"]], field="tags", message="Enter a list of values.")
        # A plain string is not ok
        self.bad(tags="abc", field="tags", message="Enter a list of values.")

    def test_comment_field(self) -> None:
        """Check that comments are validated correctly"""
        self.good(comment="")
        self.good(comment="This comment is false.")
        self.good(comment=1)


class TestEditEntryFormValidation(TestCreateEntryFormValidation):
    entries = [
        Entry(amount=1.0, date=SAMPLE_DATE, category=Tag("category1")),
        Entry(amount=2.0, date=SAMPLE_DATE, category=Tag("category1")),
        Entry(amount=3.0, date=SAMPLE_DATE, category=Tag("category1")),
    ]

    @classmethod
    def construct_entry_form(
        cls,
        *,
        category: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        entry_id: Optional[int] = None,
        **kwargs: Any,
    ) -> EditEntryForm:
        """Create a form with the given fields"""
        data = dict(
            super().construct_entry_form(category=category, tags=tags, **kwargs).data
        )
        if entry_id is not None:
            data["id"] = entry_id
        return EditEntryForm(data=data)

    def test_id_valid(self) -> None:
        """Check that the form is valid when the entry id is (convertible to) an int"""
        for entry in Entry.objects.all():
            self.good(entry_id=entry.id)
            self.good(entry_id=str(entry.id))
            self.good(entry_id=float(entry.id))
            self.good(entry_id=entry.id + 0.1)

    def test_id_wrong_type(self) -> None:
        """Check that in id of the wrong type fails validation"""
        self.bad(entry_id="", field="id", message="This field is required.")
        self.bad(
            entry_id="a",
            field="id",
            message=(
                "Select a valid choice. "
                "That choice is not one of the available choices."
            ),
        )
        self.bad(entry_id=None, field="id", message="This field is required.")

    def test_id_out_of_range(self) -> None:
        """Check that an id for a non-existent entry fails validation"""
        self.bad(
            entry_id=0,
            field="id",
            message=(
                "Select a valid choice. "
                "That choice is not one of the available choices."
            ),
        )
        self.bad(
            entry_id=self.entry_count + 1,
            field="id",
            message=(
                "Select a valid choice. "
                "That choice is not one of the available choices."
            ),
        )

    def test_queryset_update(self) -> None:
        """Check that the set of allowable ids updates when new entries are created"""
        starting_entry_count = self.entry_count
        new_entry = Entry(amount=4.0, date=SAMPLE_DATE, category=Tag("category1"))
        self.bad(
            entry_id=starting_entry_count + 1,
            field="id",
            message=(
                "Select a valid choice. "
                "That choice is not one of the available choices."
            ),
        )

        new_entry.save()
        self.good(entry_id=new_entry.id)
        self.good(entry_id=starting_entry_count + 1)

        new_entry.delete()
        self.bad(
            entry_id=starting_entry_count + 1,
            field="id",
            message=(
                "Select a valid choice. "
                "That choice is not one of the available choices."
            ),
        )


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
        form = CreateEntryForm()
        category_queryset = form.fields[
            "category"
        ].queryset  # type: ignore[attr-defined]
        self.assertQuerysetEqual(
            category_queryset,
            [Tag("red"), Tag("green"), Tag("blue")],
        )

    def test_tags_order(self) -> None:
        """Tag choices should be in descending order of prevalence"""
        form = CreateEntryForm()
        tags_queryset = form.fields["tags"].queryset  # type: ignore[attr-defined]
        self.assertQuerysetEqual(
            tags_queryset,
            [Tag("blue"), Tag("green"), Tag("red")],
        )
