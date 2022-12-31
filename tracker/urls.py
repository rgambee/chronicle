from django.urls import path

from tracker import views

urlpatterns = [
    path("", views.index, name="index"),
    path("entry/<int:pk>/", views.EntryDetailView.as_view(), name="entry"),
    path("entries/", views.EntryListAndCreate.as_view(), name="entries"),
    path(
        "entries/<str:category>/",
        views.EntryListAndCreate.as_view(),
        name="entries-in-category",
    ),
    path("edit/<int:pk>/", views.EntryEdit.as_view(), name="edit"),
]
