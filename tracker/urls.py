from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from tracker import views

urlpatterns = [
    path("", views.index, name="index"),
    path("entry/<int:pk>/", views.EntryDetailView.as_view(), name="entry"),
    path("entries/", views.EntryListAndCreate.as_view(), name="entries"),
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
    path("edit/<int:pk>/", views.EntryEdit.as_view(), name="edit"),
    path("delete/<int:pk>/", views.EntryDelete.as_view(), name="delete"),
    path("plot/", views.plot, name="plot"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
