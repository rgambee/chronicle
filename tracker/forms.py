from typing import Any

from django import forms
from django.utils import timezone

from tracker.models import Entry, Tag


class EntryForm(forms.ModelForm):  # type: ignore[type-arg]
    """A form for creating or editing an Entry

    Most validations are derived from the model. On top of that, amount is required to
    be non-negative.
    """

    amount = forms.FloatField(min_value=0.0)
    date = forms.DateTimeField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    category = forms.ModelChoiceField(queryset=None, empty_label=None)
    tags = forms.ModelMultipleChoiceField(queryset=None, required=False)

    class Meta:
        model = Entry
        fields = [
            "date",
            "amount",
            "category",
            "tags",
            "comment",
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Sort the choices for the category and tags by the number of matching Entries,
        # descending so the most common appear fist.
        category_qs = Tag.most_common_categories()
        tag_qs = Tag.most_common_tags()
        self.fields["category"].queryset = category_qs  # type: ignore[attr-defined]
        self.fields["tags"].queryset = tag_qs  # type: ignore[attr-defined]
        if category_qs:
            self.fields["category"].initial = category_qs[0]
