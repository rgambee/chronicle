import json
import logging
from typing import Any, Dict, Mapping, Tuple

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse

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


def _success(updates_data: Dict[str, Any]) -> EntryUpdatesResponse:
    return redirect(reverse("entries")), updates_data


def _failure(message: str) -> EntryUpdatesResponse:
    return HttpResponseBadRequest(message.encode("utf-8")), {}
