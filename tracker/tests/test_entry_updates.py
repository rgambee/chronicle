import json
import logging
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Union

from django.utils import timezone

from tracker.entry_updates import EntryUpdatesResponse, parse_updates, validate_updates
from tracker.models import Entry, Tag
from tracker.tests.utils import SAMPLE_DATE, TrackerTestCase


class BaseUpdateProcessing(TrackerTestCase):
    """Parent class for testing update processing"""

    tags = [Tag("red"), Tag("green"), Tag("blue")]
    entries = [
        Entry(amount=1.0, date=SAMPLE_DATE, category=Tag("red")),
        Entry(amount=2.0, date=SAMPLE_DATE, category=Tag("red")),
        Entry(amount=3.0, date=SAMPLE_DATE, category=Tag("green")),
    ]

    EXAMPLE_UPDATES: Mapping[str, Sequence[Any]] = {
        "deletions": [1],
        "edits": [
            {
                "id": 2,
                "amount": 5,
                "date": "2000-03-21",
                "category": "stuff",
                "tags": ["red", "green", "blue"],
                "comment": "Here's an example of an entry update",
            },
        ],
    }

    def base_assert_good(
        self,
        function_call: Callable[..., EntryUpdatesResponse],
        *args: Any,
        **kwargs: Any,
    ) -> EntryUpdatesResponse:
        """Assert that the function call results in a success"""
        response, updates = function_call(*args, **kwargs)
        self.assertLess(response.status_code, 400)
        return response, updates

    def base_assert_bad(
        self,
        function_call: Callable[..., EntryUpdatesResponse],
        *args: Any,
        **kwargs: Any,
    ) -> EntryUpdatesResponse:
        """Assert that the function call results in a failure"""
        with self.assertLogs(logger=None, level=logging.ERROR):
            response, updates = function_call(*args, **kwargs)
        self.assertGreaterEqual(response.status_code, 400)
        self.assertEqual(updates, {})
        return response, updates


class TestUpdatesParsing(BaseUpdateProcessing):
    def assert_good(self, form_data: Mapping[str, Any]) -> None:
        self.base_assert_good(parse_updates, form_data)

    def assert_bad(self, form_data: Mapping[str, Any]) -> None:
        self.base_assert_bad(parse_updates, form_data)

    def test_missing_updates(self) -> None:
        """A missing "updates" key is invalid"""
        self.assert_bad({})

    def test_empty_updates(self) -> None:
        """An update list of zero length is acceptable"""
        self.assert_good({"updates": []})

    def test_multiple_updates(self) -> None:
        """An update list with more than one element is invalid"""
        self.assert_bad({"updates": ["{}", "{}"]})

    def test_invalid_json(self) -> None:
        """Invalid JSON should be caught and result in a failure response"""
        self.assert_bad({"updates": [""]})
        self.assert_bad({"updates": ["{"]})
        self.assert_bad({"updates": ["{'wrong quotes': 'value'}"]})
        self.assert_bad({"updates": ['{"trailing comma": "value",}']})

    def test_valid_updates(self) -> None:
        """Valid JSON should result in a success response"""
        self.assert_good({"updates": [json.dumps(self.EXAMPLE_UPDATES)]})


class TestUpdatesValidation(BaseUpdateProcessing):
    @classmethod
    def construct_data(
        cls,
        deletions: Optional[Sequence[int]] = None,
        edits: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Modify the example update data"""
        if edits is None:
            edits = {}
        data = dict(cls.EXAMPLE_UPDATES)
        if deletions is not None:
            data["deletions"] = deletions
        # This line avoids modifying the contents of the shared EXAMPLE_UPDATES dict
        data["edits"] = [data["edits"][0] | edits]
        return data

    def assert_good(
        self,
        data: Optional[Mapping[str, Any]] = None,
        deletions: Optional[Sequence[int]] = None,
        edits: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Check that the example data is considered valid"""
        if data is None:
            data = self.construct_data(deletions, edits)
        _, validated_data = self.base_assert_good(validate_updates, data)
        self.assertEqual(len(data["deletions"]), len(validated_data["deletions"]))
        self.assertEqual(len(data["edits"]), len(validated_data["edits"]))
        return validated_data

    def assert_bad(
        self,
        data: Optional[Mapping[str, Any]] = None,
        deletions: Optional[Sequence[int]] = None,
        edits: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Check that the example data is considered invalid"""
        if data is None:
            data = self.construct_data(deletions, edits)
        _, data = self.base_assert_bad(validate_updates, data)
        return data

    def test_empty_updates(self) -> None:
        """An empty data dict should result in a success response"""
        _, validated_data = self.base_assert_good(validate_updates, {})
        self.assertEqual(validated_data["deletions"], [])
        self.assertEqual(validated_data["edits"], [])

    def test_deletion_empty(self) -> None:
        """Deleting no entries should result in a success response"""
        self.assert_good(deletions=[])

    def test_deletion_invalid_id(self) -> None:
        """Deleting a non-existent entry should result in a failure response"""
        self.assert_bad(deletions=[0])
        self.assert_bad(deletions=[Entry.objects.count() + 1])

    def test_edit_empty(self) -> None:
        """Edit no entries should result in a success response"""
        data = dict(self.EXAMPLE_UPDATES)
        data["edits"] = []
        self.assert_good(data)

    def test_edit_invalid_id(self) -> None:
        """Editing a non-existent entry should result in a failure response"""
        self.assert_bad(edits={"id": 0})
        self.assert_bad(edits={"id": Entry.objects.count() + 1})

    def test_edit_missing_fields(self) -> None:
        """Leaving out any required fields should result in a failed response

        test_forms.py also covers these scenarios
        """
        good_edit = dict(self.EXAMPLE_UPDATES["edits"][0])
        edit: Dict[str, Any] = {}
        data: Mapping[str, Sequence[Any]] = {"deletions": [], "edits": [edit]}
        self.assert_bad(data)

        edit.update(good_edit)
        self.assert_good(data)
        for required_field in ("id", "amount", "date", "category"):
            with self.subTest(required_field=required_field):
                del edit[required_field]
                self.assert_bad(data)
                edit[required_field] = None
                self.assert_bad(data)
                edit[required_field] = ""
                self.assert_bad(data)
                edit[required_field] = good_edit[required_field]

        for optional_field in ("tags", "comment"):
            with self.subTest(optional_field=optional_field):
                del edit[optional_field]
                self.assert_good(data)
                edit[optional_field] = None
                self.assert_good(data)
                edit[optional_field] = ""
                self.assert_good(data)

    def test_edit_types(self) -> None:
        """Using the wrong field types should result in a failed response

        This also checks that new values (i.e. ones that aren't already in the database)
        can be provided for the category and tags fields.

        test_forms.py also covers these scenarios
        """
        # String fields don't have to be strings initially; they'll be converted
        for field in ("category", "comment"):
            for value in (123, True, [1, 2, 3]):
                validated_data = self.assert_good(edits={field: value})
                expected_value: Union[str, Tag] = str(value)
                if field == "category":
                    expected_value = Tag(str(value))
                self.assertEqual(
                    validated_data["edits"][0].cleaned_data[field],
                    expected_value,
                )

        self.assert_bad(edits={"tags": "one_tag"})
        validated_data = self.assert_good(edits={"tags": ["list", "of", "tags"]})
        self.assertQuerysetEqual(
            validated_data["edits"][0].cleaned_data["tags"],
            [Tag("list"), Tag("of"), Tag("tags")],
        )

    def test_edit_values(self) -> None:
        """Using the wrong field values should result in a failed response

        test_forms.py also covers these scenarios
        """
        for field in ("id", "amount"):
            with self.subTest(field=field):
                self.assert_bad(edits={field: "abc"})
                validated_data = self.assert_good(edits={field: "1"})
                cleaned_value = validated_data["edits"][0].cleaned_data[field]
                if field == "id":
                    self.assertIsInstance(cleaned_value, Entry)
                    self.assertEqual(cleaned_value.id, 1)
                else:
                    self.assertEqual(cleaned_value, 1)

        # Amount must be non-negative
        validated_data = self.assert_good(edits={"amount": "0.0"})
        self.assertEqual(validated_data["edits"][0].cleaned_data["amount"], 0.0)
        self.assert_bad(edits={"amount": -1})

        # Date can't be a Unix timestamp
        self.assert_bad(edits={"date": str(int(1e9))})
        # Date can be in various formats
        expected_date = timezone.make_aware(timezone.datetime(2000, 1, 23))
        for date in ("2000-01-23", "1/23/2000", "23 January 2000"):
            with self.subTest(date=date):
                validated_data = self.assert_good(edits={"date": date})
                self.assertEqual(
                    validated_data["edits"][0].cleaned_data["date"],
                    expected_date,
                )
