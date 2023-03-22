import json
import logging
from typing import Any, Callable, Dict, Mapping, Sequence

from django.test import TestCase

from tracker.entry_updates import EntryUpdatesResponse, parse_updates


class BaseUpdateProcessing(TestCase):
    """Parent class for testing update processing"""

    EXAMPLE_UPDATES: Dict[str, Sequence[Any]] = {
        "deletions": [42],
        "edits": [
            {
                "id": 123,
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
