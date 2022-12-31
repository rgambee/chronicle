from typing import Any

from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, ListView
from django.views.generic.edit import UpdateView

from tracker.forms import EntryForm
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


class EntryListView(ListView):  # type: ignore[type-arg]
    """View a list of many entries"""

    model = Entry
    paginate_by = 100
    context_object_name = "entries"

    def get_queryset(self) -> QuerySet[Entry]:
        if "category" in self.kwargs:
            return Entry.objects.filter(category=self.kwargs["category"])
        return Entry.objects.all()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(form=EntryForm(), **kwargs)


class EntryCreate(FormView):  # type: ignore[type-arg]
    """Create a new entry using a form"""

    model = Entry
    form_class = EntryForm
    template_name = "tracker/entry_list.html"

    def form_valid(self, form: EntryForm) -> HttpResponse:
        """If the form is valid, save the associated model.

        Copied from the ModelFormMixin.
        """
        form.save()
        return super().form_valid(form)

    def get_success_url(self) -> str:
        if "category" in self.kwargs:
            return reverse(
                "entries-in-category", kwargs=dict(category=self.kwargs["category"])
            )
        return reverse("entries")


class EntryEdit(UpdateView):  # type: ignore[type-arg]
    """Edit an existing entry using a form"""

    model = Entry
    form_class = EntryForm
    success_view = "new/"


class EntryListAndCreate(View):
    """Combine EntryListView and EntryCreate

    This shows the list of existing entries and a form for creating a new one on the
    same page.
    """

    def get(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        view = EntryListView.as_view()
        return view(*args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        view = EntryCreate.as_view()
        return view(*args, **kwargs)
