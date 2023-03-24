from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from tracker import views

urlpatterns = [
    path(
        "",
        views.index,
        name="index",
    ),
    path(
        "entry/<int:pk>/",
        views.EntryDetailView.as_view(),
        name="entry",
    ),
    path(
        "entries/",
        views.EntryListAndCreate.as_view(),
        name="entries",
    ),
    path(
        "entries/<str:category>/<int:amount><str:unit>/",
        views.EntryListAndCreate.as_view(),
        name="recent-in-category",
    ),
    path(
        "entries/<int:amount><str:unit>/",
        views.EntryListAndCreate.as_view(),
        name="entries-recent",
    ),
    path(
        "entries/<str:category>/",
        views.EntryListAndCreate.as_view(),
        name="entries-in-category",
    ),
    path(
        "updates/",
        views.update_entries,
        name="updates",
    ),
    path(
        "charts/",
        views.ChartView.as_view(),
        name="charts",
    ),
    path(
        "charts/<int:amount><str:unit>/",
        views.ChartView.as_view(),
        name="charts-recent",
    ),
] + static(
    settings.STATIC_URL,
    document_root=settings.STATIC_ROOT,
)
