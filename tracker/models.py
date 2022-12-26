from django.db import models


def get_empty_tag() -> "Tag":
    """Get the empty Tag, or create it if it doesn't exist"""
    tag, _ = Tag.objects.get_or_create(name="")  # pylint: disable=no-member
    return tag


class Tag(models.Model):
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


class Entry(models.Model):
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
        if self.id is not None:  # pylint: disable=no-member
            tags = ", ".join(
                str(t) for t in self.tags.all()  # pylint: disable=no-member
            ).join("[]")
        return (
            f"{self.__class__.__name__}"
            f"(date={self.date:%Y-%m-%d}, "
            f"amount={self.amount:.0f}, "
            f"category={self.category}, "
            f"tags={tags})"
        )
