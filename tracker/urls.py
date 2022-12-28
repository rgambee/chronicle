from django.urls import path

from tracker import views

urlpatterns = [
    path("", views.index, name="index"),
    path("entry/<int:pk>/", views.EntryDetailView.as_view(), name="entry"),
    path("entries/", views.EntryListView.as_view(), name="entries"),
    path("new/", views.EntryCreate.as_view(), name="new"),
    path("edit/<int:pk>/", views.EntryEdit.as_view(), name="edit"),
]
