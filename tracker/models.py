from django.db import models
from django.db.models.query import QuerySet
from django.urls import reverse


def get_empty_tag() -> "Tag":
    """Get the empty Tag, or create it if it doesn't exist"""
    tag, _ = Tag.objects.get_or_create(name="")
    return tag


class Tag(models.Model):
    """A Tag is a short string used to group Entries.

    Tags are unique, so there isn't an id column.

    A Tag may be blank (i.e. the empty string) but not null.
    """

    name = models.CharField(
        max_length=50,
        primary_key=True,
        unique=True,
        null=False,
        blank=True,
    )

    def __str__(self) -> str:
        if not self.name:
            return "<unset>"
        return str(self.name)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    @staticmethod
    def most_common_categories() -> QuerySet["Tag"]:
        return (
            Tag.objects.exclude(name="")
            .annotate(num_entries=models.Count("entries_in_category"))
            .order_by("-num_entries")
        )

    @staticmethod
    def most_common_tags() -> QuerySet["Tag"]:
        return (
            Tag.objects.exclude(name="")
            .annotate(num_entries=models.Count("tagged_entries"))
            .order_by("-num_entries")
        )


class Entry(models.Model):
    """An Entry is the main unit of data this app deals with.

    Each one represents an amount of some sort, along with metadata describing when and
    how it was allocated.

    Fields
        amount: The amount of some resource that was gained or lost, e.g. hours of time
            spent on a task. In principle this could be negative or positive, for
            instance to represent income and expenditures. However, at this time most of
            the rest of the app assumes the amount is always positive.
        date: The date when the resource was acquired or spent, which may be different
            from the date this Entry was created. It's saved as a datetime for future-
            proofing, though the rest of the app presently only uses the date portion.
        category: The primary Tag used to group this Entry.
        tags: Secondary Tags for additional grouping and filtering.
        comment: A general text field for the user to save notes about this Entry.
    """

    # DecimalField would be a good choice since it would make arithmetic more precise.
    # However, SQLite doesn't support decimal types.
    amount = models.FloatField()
    date = models.DateTimeField()
    category = models.ForeignKey(
        Tag,
        db_column="category",
        related_name="entries_in_category",
        on_delete=models.SET(get_empty_tag),
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="tagged_entries")
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "entries"

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(date={self.date:%Y-%m-%d}, "
            f"amount={self.amount:.0f})"
        )

    def __repr__(self) -> str:
        tags = "[]"
        if self.id is not None:
            tags = ", ".join(str(t) for t in self.tags.all()).join("[]")
        return (
            f"{self.__class__.__name__}"
            f"(date={self.date:%Y-%m-%d}, "
            f"amount={self.amount:.0f}, "
            f"category={self.category}, "
            f"tags={tags})"
        )

    def get_absolute_url(self) -> str:
        return reverse("entry", kwargs=dict(pk=self.id))
