from typing import Any, Optional

from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, ListView
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
        if "category" in self.kwargs:
            return Entry.objects.filter(category=self.kwargs["category"])
        return Entry.objects.all()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(
            form=EntryForm(selected_category=self.selected_category),
            **kwargs,
        )


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
        view = EntryListView.as_view(selected_category=kwargs.get("category"))
        return view(*args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        view = EntryCreate.as_view()
        return view(*args, **kwargs)


class EntryDelete(DeleteView):  # type: ignore[type-arg]
    """Delete an entry, after asking for confirmation"""

    model = Entry
    context_object_name = "entry"
    success_url = reverse_lazy("entries")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # This view uses the same template as EntryDetailView. In this view, we don't
        # want to show a delete link since we're already at that view.
        context["show_delete_link"] = False
        return context
