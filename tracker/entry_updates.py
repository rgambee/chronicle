import json
import logging
from typing import Any, Dict, List, Mapping, Tuple

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse

from tracker.forms import EditEntryForm
from tracker.models import Entry

EntryUpdatesResponse = Tuple[HttpResponse, Dict[str, Any]]


def parse_updates(form_data: Mapping[str, Any]) -> EntryUpdatesResponse:
    """Parse the form data and deserialize the enclosed JSON"""
    if "updates" not in form_data:
        message = "No 'updates' key"
        logging.error(message)
        return _failure(message)
    updates = form_data["updates"]
    if len(updates) == 0:
        return _success({})
    if len(updates) > 1:
        message = "Too many update elements provided"
        logging.error(message)
        return _failure(message)

    try:
        decoded_data = json.loads(updates[0])
    except json.JSONDecodeError as err:
        logging.error("Failed to parse updates: %r", err)
        return _failure("Failed to parse updates")
    return _success(decoded_data)


def validate_updates(parsed_data: Mapping[str, Any]) -> EntryUpdatesResponse:
    """Validate the requested entry updates

    This consists of checking that edits to existing entries are valid and that the
    IDs to delete refer to existing entries.
    """
    # Validate the edits to existing entries. This includes checking that the IDs refer
    # to existing entries.
    forms: List[EditEntryForm] = []
    for entry in parsed_data.get("edits", []):
        form = EditEntryForm(entry)
        if not form.is_valid():
            logging.error("Failed to validate entry edit: %r", form.errors)
            return _failure("Failed to validate entry edit")
        forms.append(form)

    # Check that the IDs for deleted entries are valid and refer to existing entries.
    deletions: List[int] = []
    for unvalidated_id in parsed_data.get("deletions", []):
        try:
            validated_id = int(unvalidated_id)
        except ValueError as err:
            logging.error("Failed to convert entry ID to int: %r", err)
            return _failure("Failed to convert entry ID to int")
        try:
            Entry.objects.get(pk=validated_id)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            logging.error("Failed to find Entry corresponding to id %d", validated_id)
            return _failure("Failed to find matching Entry")
        deletions.append(validated_id)

    return _success({"edits": forms, "deletions": deletions})


def _success(updates_data: Dict[str, Any]) -> EntryUpdatesResponse:
    return redirect(reverse("entries")), updates_data


def _failure(message: str) -> EntryUpdatesResponse:
    return HttpResponseBadRequest(message.encode("utf-8")), {}
