from django.urls import path

from gradia.contest.views import (
    ContestDetailView,
    ContestListView,
    EstablishmentDetailView,
    EstablishmentListView,
    SessionDetailView,
)

app_name = "contest"

urlpatterns = [
    path("", ContestListView.as_view(), name="list"),
    path(
        "etablissement/",
        EstablishmentListView.as_view(),
        name="establishment_list",
    ),
    path(
        "etablissement/<slug:slug>/",
        EstablishmentDetailView.as_view(),
        name="establishment_detail",
    ),
    path("<slug:slug>/", ContestDetailView.as_view(), name="detail"),
    path(
        "<slug:contest_slug>/<int:year>/",
        SessionDetailView.as_view(),
        name="session_detail",
    ),
]
