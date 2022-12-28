from django.db.models import Count
from django.forms import (
    FloatField,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
)

from tracker.models import Entry, Tag


class EntryForm(ModelForm):  # type: ignore[type-arg]
    """A form for creating or editing an Entry

    Most validations are derived from the model. On top of that, amount is required to
    be non-negative.
    """

    amount = FloatField(min_value=0.0)
    # Sort the choices for the category and tags by the number of matching Entries,
    # descending so the most common appear fist.
    category = ModelChoiceField(
        queryset=Tag.objects.exclude(name="")
        .annotate(num_entries=Count("entries_in_category"))
        .order_by("-num_entries")
    )
    tags = ModelMultipleChoiceField(
        queryset=Tag.objects.exclude(name="")
        .annotate(num_entries=Count("tagged_entries"))
        .order_by("-num_entries"),
        required=False,
    )

    class Meta:
        model = Entry
        fields = [
            "date",
            "amount",
            "category",
            "tags",
            "comment",
        ]