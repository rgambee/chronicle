from typing import Optional, Sequence

from django.test import TestCase
from django.utils import timezone

from tracker.models import Entry, Tag

SAMPLE_DATE = timezone.make_aware(timezone.datetime(2001, 1, 23))


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


class TrackerTestCase(TestCase):
    tags: Optional[Sequence[Tag]] = None
    entries: Optional[Sequence[Entry]] = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        init_db(tags=cls.tags, entries=cls.entries)
