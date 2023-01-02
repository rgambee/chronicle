from typing import Optional, Sequence

from django.test import TestCase
from django.utils import timezone

from tracker.forms import EntryForm
from tracker.models import Entry, Tag

SAMPLE_DATE = timezone.make_aware(timezone.datetime(2001, 1, 23))


class TrackerTestCase(TestCase):
    """Parent class to help populate test database"""

    tags: Optional[Sequence[Tag]] = None
    entries: Optional[Sequence[Entry]] = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        init_db(tags=cls.tags, entries=cls.entries)

    @property
    def entry_count(self) -> int:
        return Entry.objects.count()


def init_db(
    tags: Optional[Sequence[Tag]] = None,
    entries: Optional[Sequence[Entry]] = None,
) -> None:
    """Poplulate the test database with some sample data

    tags and entries may be given explicitly. If so, they'll simply be saved as-is. If
    either isn't provided, some defaults will be saved instead.
    """
    if tags is None:
        tags = (Tag("stuff"), Tag("things"))
    if entries is None:
        entries = []
        for i in range(3):
            category = Tag("")
            if len(tags) > 0:
                category = tags[i % len(tags)]
            entries.append(Entry(amount=i, date=SAMPLE_DATE, category=category))

    for tag in tags:
        tag.save()
    for entry in entries:
        entry.save()


def construct_entry_form(
    *,
    amount: float = 1.234,
    date: str = "2000-01-31",
    category: Optional[str] = None,
    tags: Sequence[str] = tuple(),
    comment: str = "Example comment",
) -> EntryForm:
    """Construct an EntryForm with some default field values

    Any field can be overridden.

    Category and tags default to ones already in the database, e.g. from calling
    init_db().

    If no tags have been added to the database and category is not provided, the
    returned EntryForm will not pass validation.
    """
    if category is None or tags is None:
        existing_tags = Tag.objects.all()
        if existing_tags:
            if category is None:
                category = existing_tags[0].name
            if tags is None:
                tags = [tag.name for tag in existing_tags]
    return EntryForm(
        data=dict(
            amount=amount,
            date=date,
            category=category,
            tags=tags,
            comment=comment,
        )
    )
