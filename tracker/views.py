from django.http import HttpRequest, HttpResponse
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView

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
    model = Entry
    context_object_name = "entry"


class EntryListView(ListView):  # type: ignore[type-arg]
    model = Entry
    paginate_by = 100
    context_object_name = "entries"


class EntryCreate(CreateView):  # type: ignore[type-arg]
    model = Entry
    form_class = EntryForm
    success_view = "new/"


class EntryEdit(UpdateView):  # type: ignore[type-arg]
    model = Entry
    form_class = EntryForm
    success_view = "new/"
