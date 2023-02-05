import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Sum
from django.db.models.query import QuerySet
from django.forms import Form
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBase
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, ListView
from django.views.generic.edit import CreateView, UpdateView

from tracker.forms import EntryForm, PreferencesForm
from tracker.models import Entry


def index(_: HttpRequest) -> HttpResponse:
    """Placeholder view for the root url"""
    return HttpResponse("index")


# These parent *View classes are generic class but don't have __class_getitem__()
# methods, which prevents one from specifying the type parameter. The
# django-stubs-ext package has a monkeypatch to address this, but that imposes runtime
# dependencies.
class EntryDetailView(DetailView):  # type: ignore[type-arg]
    """View the contents of a single entry"""

    model = Entry
    context_object_name = "entry"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # This view uses the same template as EntryDelete. In this view, we want to show
        # a link to point to let the user delete this entry.
        context["show_delete_link"] = True
        return context


class EntryListView(ListView):  # type: ignore[type-arg]
    """View a list of many entries"""

    model = Entry
    paginate_by = 100
    context_object_name = "entries"
    selected_category: Optional[str] = None

    def get_queryset(self) -> QuerySet[Entry]:
        queryset = Entry.objects.all()
        if "category" in self.kwargs:
            queryset = queryset.filter(category=self.kwargs["category"])
        try:
            queryset = get_recent_entries(
                queryset, self.kwargs.get("amount"), self.kwargs.get("unit")
            )
        except (TypeError, ValueError) as err:
            raise Http404("Invalid date range") from err
        return queryset

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(
            form=EntryForm(selected_category=self.selected_category),
            **kwargs,
        )


class EntryCreate(SuccessMessageMixin, CreateView):  # type: ignore[type-arg]
    """Create a new entry using a form"""

    model = Entry
    form_class = EntryForm
    template_name = "tracker/entry_list.html"
    success_message = "Entry on %(date)s was created successfully"

    def get_success_url(self) -> str:
        if "category" in self.kwargs:
            return reverse(
                "entries-in-category", kwargs=dict(category=self.kwargs["category"])
            )
        return reverse("entries")

    def get_success_message(self, cleaned_data: dict[str, Any]) -> str:
        return self.success_message % dict(date=cleaned_data["date"].date())


class EntryEdit(SuccessMessageMixin, UpdateView):  # type: ignore[type-arg]
    """Edit an existing entry using a form"""

    model = Entry
    form_class = EntryForm
    success_view = "new/"
    success_message = "Entry on %(date)s was updated successfully"

    def get_success_message(self, cleaned_data: dict[str, Any]) -> str:
        return self.success_message % dict(date=cleaned_data["date"].date())


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


class EntryDelete(SuccessMessageMixin, DeleteView):  # type: ignore[type-arg, misc]
    """Delete an entry, after asking for confirmation"""

    model = Entry
    context_object_name = "entry"
    success_url = reverse_lazy("entries")
    success_message = "Entry was deleted successfully"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # This view uses the same template as EntryDetailView. In this view, we don't
        # want to show a delete link since we're already at that view.
        context["show_delete_link"] = False
        return context


class PlotView(ListView):  # type: ignore[type-arg]
    """Visualize entries with plots"""

    model = Entry
    template_name = "tracker/plot.html"

    def get_queryset(self) -> QuerySet[Entry]:
        return get_recent_entries(
            Entry.objects.all(),
            self.kwargs.get("amount"),
            self.kwargs.get("unit"),
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(
            # aggregate_entries() expects a QuerySet, while object_list has the more
            # general type SupportsPagination. In the case of this class, object_list
            # is indeed a QuerySet, as returned by get_queryset(). If a child class were
            # to override get_queryset() to turn a different type, that could cause an
            # issue. But it's unlikely and can be addressed in the future if necessary.
            entries=aggregate_entries(self.object_list),  # type: ignore[arg-type]
            **kwargs,
        )


class PreferencesEdit(FormView):  # type: ignore[type-arg]
    """View for editing user preferences"""

    template_name = "tracker/preferences.html"
    form_class = PreferencesForm
    success_url = reverse_lazy("entries")

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        logging.info(request.session.items())
        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        logging.info(request.session.items())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form: Form) -> HttpResponse:
        logging.info(form.cleaned_data)
        return super().form_valid(form)


def get_recent_entries(
    queryset: QuerySet[Entry],
    amount: Optional[int] = None,
    unit: Optional[str] = None,
    end: Optional[datetime] = None,
) -> QuerySet[Entry]:
    """Filter the given queryset to only contain recent entries

    See the documentation for subtract_timedelta() for the requirements regarding the
    `amount` and `unit` arguments.

    `end` defaults to now.
    """
    if amount is not None and unit is not None:
        if end is None:
            end = timezone.now()
        try:
            start = subtract_timedelta(end, amount, unit)
        except (TypeError, ValueError) as err:
            raise Http404("Invalid date range") from err
        queryset = queryset.filter(date__gte=start).filter(date__lte=end)
    elif amount is not None or unit is not None:
        logging.error("Invalid arguments: amount=%s, unit=%s", amount, unit)
        raise TypeError("Must provide both amount and unit or neither")
    return queryset


def subtract_timedelta(end: datetime, amount: int, unit: str) -> datetime:
    """Subtract the given amount of time from an end date

    `amount` must be a non-negative integer.

    `unit` may be one of the following:
        "years"
        "months"
        "weeks"
        "days"
        "hours"
        "minutes"
        "seconds"
    """
    if amount < 0:
        raise ValueError("Time delta amount may not be negative")
    if unit == "years":
        start = end.replace(year=end.year - amount)
    elif unit == "months":
        month = (end.month - amount - 1) % 12 + 1
        year = end.year + (end.month - amount - 1) // 12
        try:
            start = end.replace(year=year, month=month)
        except ValueError as err:
            if str(err) == "day is out of range for month":
                # Round invalid dates (like February 30th) forward to next valid one
                year += month // 12
                month = month % 12 + 1
                start = end.replace(year=year, month=month, day=1)
            else:
                raise
    else:
        delta = timedelta(**{unit: amount})
        start = end - delta
    return start


def aggregate_entries(queryset: QuerySet[Entry]) -> dict[str, dict[str, float]]:
    """Group entries first by category, then by date"""
    # Determine unique categories and dates
    categories = queryset.order_by("category_id").values("category_id").distinct()
    dates = queryset.datetimes(field_name="date", kind="day")
    # For each (category, date) pair, sum the amounts of the corresponding entries
    aggregated: dict[str, dict[str, float]] = {}
    for cat in categories:
        aggregated[cat["category_id"]] = {}
        for day in dates:
            total = queryset.filter(
                category=cat["category_id"],
                date__date=day.date(),
            ).aggregate(Sum("amount"))
            if total["amount__sum"]:
                formatted_date = format_datetime_ecma(day)
                aggregated[cat["category_id"]][formatted_date] = total["amount__sum"]
    return aggregated


def format_datetime_ecma(when: datetime) -> str:
    """Format the given datetime according to the official ECMAScript spec

    This aims to ensure maximum compatibility with different browsers.

    The spec is defined here:
    https://tc39.es/ecma262/#sec-date-time-string-format
    """
    return when.isoformat(timespec="milliseconds")
