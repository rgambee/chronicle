import logging
import uuid
from typing import Any, Iterable, Optional

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.db.models.query import QuerySet
from django.forms.widgets import ChoiceWidget, SelectMultiple
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

    def get_context(
        self,
        name: str,
        value: str,
        attrs: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        # Inert the input type into the context for the template to use. The parent
        # class doesn't do this, presumably because it expects to always be rendered
        # with a <select> tag.
        context["widget"] = context.get("widget", {}) | {"type": self.input_type}
        return context

    def format_value(self, value: Any) -> str:  # type: ignore[override]
        # ChoiceWidget.format_value() always returns a list for some reason. Perhaps
        # it's because it needs to support multiple ones being selected? That's not
        # necessary in this case. And returning a list causes the HTML value to be
        # rendered as `value="['myvalue']"` instead of `value="myvalue"`. Therefore, we
        # return the first element of the list.
        logger = logging.getLogger(__name__)
        values = super().format_value(value)
        if len(values) < 1:
            logger.warning("Received no values to format")
            return ""
        if len(values) > 1:
            logger.warning("Received multiple values to format: %s", values)
        return values[0]


class TagsWidget(SelectMultiple):
    template_name = "tracker/widgets/tags.html"


class GetOrCreateChoiceField(forms.ModelChoiceField):
    """Variant of ModelChoiceField that creates the object if it doesn't exist

    Ideally, the object would only be created if all the other validation checks pass.
    But that's challenging to implement and unlikely to make a noticeable difference to
    the user.
    """

    def to_python(self, value: Any) -> Optional[Model]:
        """Create a new object for this value if it doesn't already exist"""
        if value not in self.empty_values:
            if self.queryset is None:
                raise TypeError("queryset has not been set")
            key = self.to_field_name or "pk"
            self.queryset.get_or_create(**{key: value})
        return super().to_python(value)


class GetOrCreateMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Variant of ModelMultipleChoiceField that creates objects if they don't exist

    Ideally, the objects would only be created if all the other validation checks pass.
    But that's challenging to implement and unlikely to make a noticeable difference to
    the user.
    """

    def _check_values(self, value: Iterable[Any]) -> QuerySet[Model]:
        """Check that the list of keys is valid and create objects for them if needed

        The bulk of this method is copied from the parent class's implementation. The
        end of the parent's method needs to be adjusted to not require that the objects
        already exist. The cleanest solution is to copy the first part of the method and
        append the modifications.
        """

        key_name = self.to_field_name or "pk"
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            value = frozenset(value)
        except TypeError as error:
            # list of lists isn't hashable, for example
            raise ValidationError(
                self.error_messages["invalid_list"],
                code="invalid_list",
            ) from error
        if self.queryset is None:
            raise TypeError("queryset has not been set")
        for primary_key in value:
            try:
                self.queryset.filter(**{key_name: primary_key})
            except (ValueError, TypeError) as error:
                raise ValidationError(
                    self.error_messages["invalid_pk_value"],
                    code="invalid_pk_value",
                    params={"pk": primary_key},
                ) from error
        # Create new objects for any missing that are missing. This is done in a
        # separate loop so that we know the check above has passed for each element.
        for primary_key in value:
            self.queryset.get_or_create(**{key_name: primary_key})
        return self.queryset.filter(**{f"{key_name}__in": value})


class CreateEntryForm(forms.ModelForm):  # type: ignore[type-arg]
    """A form for creating an Entry

    Most validations are derived from the model. On top of that, amount is required to
    be non-negative.
    """

    amount = forms.FloatField(
        min_value=0.0,
    )
    date = forms.DateTimeField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    category = GetOrCreateChoiceField(
        queryset=None,
        empty_label=None,
        widget=AutocompleteWidget(
            attrs={"list": "id_category_list", "spellcheck": "true"}
        ),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"autocorrect": "on", "rows": 2, "cols": 20}),
    )
    tags = GetOrCreateMultipleChoiceField(
        queryset=None,
        required=False,
        widget=TagsWidget(),
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


class EditEntryForm(CreateEntryForm):
    """A variation on CreateEntryForm used to modify existing entries"""

    id = forms.ModelChoiceField(queryset=Entry.objects.all())

    def clean(self) -> None:
        super().clean()
        # Change the model instance to the one specified by the `id` field. Somewhat
        # counterintuitively, that field's `to_python()` method resolves to a model
        # instance, not the id itself.
        # Without setting self.instance to an existing model instance, this form would
        # create a new database entry when saved. That's not what we want since this
        # form is specifically for modifying existing instances.
        # Usually, when using a form to modify an existing instance, the instance is
        # passed to the form's __init__() method. However, since the instance id is a
        # field within the form, we don't know what instance to use until we create and
        # validate the form.
        if self.is_valid():
            self.instance = self.cleaned_data["id"]
