from typing import Any, Optional

from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models.query import QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    HttpResponseNotAllowed,
)
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView
from django.views.generic.base import ContextMixin
from django.views.generic.edit import CreateView

from tracker.entry_updates import process_updates
from tracker.forms import CreateEntryForm
from tracker.models import Entry
from tracker.view_utils import get_recent_entries, prepare_entries_for_serialization


def index(_: HttpRequest) -> HttpResponse:
    """Redirect to the entry list"""
    return redirect("entries", permanent=True)


def update_entries(request: HttpRequest) -> HttpResponse:
    """Edit or delete multiple existing entries"""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    return process_updates(request.POST)


class TrackerContextMixin(ContextMixin):
    """Mixin for adding assorted info to the context for templates to use

    * navbar_links: pages that should be linked from the navbar
    * demo_mode: whether the app is running in read-only, demo mode
    """

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(
            navbar_links=["entries", "charts"],
            demo_mode=settings.DEMO_MODE,
            **kwargs,
        )


# These parent *View classes are generic class but don't have __class_getitem__()
# methods, which prevents one from specifying the type parameter. The
# django-stubs-ext package has a monkeypatch to address this, but that imposes runtime
# dependencies.
class EntryListView(TrackerContextMixin, ListView):  # type: ignore[type-arg]
    """View a list of many entries"""

    model = Entry
    paginate_by = 100
    template_name = "tracker/entry_list.html"
    context_object_name = "entries"
    selected_category: Optional[str] = None

    def get_queryset(self) -> QuerySet[Entry]:
        queryset = Entry.objects.all()
        if "category" in self.kwargs:
            queryset = queryset.filter(category=self.kwargs["category"])
        return get_recent_entries(
            queryset, self.kwargs.get("amount"), self.kwargs.get("unit")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(
            form=CreateEntryForm(selected_category=self.selected_category),
            navbar_active="entries",
            **kwargs,
        )


class EntryCreate(
    TrackerContextMixin,
    SuccessMessageMixin,
    CreateView,  # type: ignore[type-arg]
):
    """Create a new entry using a form"""

    model = Entry
    form_class = CreateEntryForm
    success_message = "Entry on %(date)s was created successfully"

    def get_success_url(self) -> str:
        if "category" in self.kwargs:
            return reverse(
                "entries-in-category", kwargs={"category": self.kwargs["category"]}
            )
        return reverse("entries")

    def get_success_message(self, cleaned_data: dict[str, Any]) -> str:
        return self.success_message % {"date": cleaned_data["date"].date()}


class EntryListAndCreate(View):
    """Combine EntryListView and EntryCreate

    This shows the list of existing entries and a form for creating a new one on the
    same page.
    """

    def get(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        view = EntryListView.as_view(selected_category=kwargs.get("category"))
        return view(*args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        view = EntryCreate.as_view()
        return view(*args, **kwargs)


class ChartView(TrackerContextMixin, ListView):  # type: ignore[type-arg]
    """Visualize entries with charts"""

    model = Entry
    template_name = "tracker/charts.html"

    def get_queryset(self) -> QuerySet[Entry]:
        return get_recent_entries(
            Entry.objects.all(),
            self.kwargs.get("amount"),
            self.kwargs.get("unit"),
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(
            entries=prepare_entries_for_serialization(self.object_list),
            navbar_active="charts",
            **kwargs,
        )
