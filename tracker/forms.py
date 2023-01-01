import logging
import uuid
from typing import Any, Optional

from django import forms
from django.forms.widgets import ChoiceWidget
from django.utils import timezone

from tracker.models import Entry, Tag


class AutocompleteWidget(ChoiceWidget):
    """A text box with autocompletion options"""

    input_type = "text"
    template_name = "tracker/widgets/autocomplete.html"
    option_template_name = "django/forms/widgets/select_option.html"
    add_id_index = False
    checked_attribute = {}
    option_inherits_attrs = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "list" not in self.attrs:
            # This needs to be unique. UUID version 1 uses the system clock. Even if two
            # instances of this class are created very close in time, they'll have
            # different timestamps.
            self.attrs["list"] = str(uuid.uuid1().time_low)

    def format_value(self, value: Any) -> str:  # type: ignore[override]
        # ChoiceWidget.format_value() always returns a list for some reason. Perhaps
        # it's because it needs to support multiple ones being selected? That's not
        # necessary in this case. And returning a list causes the HTML value to be
        # rendered as `value="['myvalue']"` instead of `value="myvalue"`. Therefore, we
        # return the first element of the list.
        values = super().format_value(value)
        if len(values) < 1:
            logging.warning("Received no values to format")
            return ""
        if len(values) > 1:
            logging.warning("Received multiple values to format: %s", values)
        return values[0]


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
    category = forms.ModelChoiceField(
        queryset=None,
        empty_label=None,
        widget=AutocompleteWidget(attrs={"list": "id_category_list"}),
    )
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

    def __init__(
        self,
        *args: Any,
        selected_category: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        # Sort the choices for the category and tags by the number of matching Entries,
        # descending so the most common appear fist.
        category_qs = Tag.most_common_categories()
        tag_qs = Tag.most_common_tags()
        self.fields["category"].queryset = category_qs  # type: ignore[attr-defined]
        self.fields["tags"].queryset = tag_qs  # type: ignore[attr-defined]
        if selected_category is not None:
            self.fields["category"].initial = selected_category
        elif category_qs:
            self.fields["category"].initial = category_qs[0]
