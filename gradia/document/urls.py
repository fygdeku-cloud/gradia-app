from django.urls import path

from gradia.document.views import (
    CorrectionDownloadView,
    CorrectionViewView,
    DocumentCreateView,
    DocumentDeleteView,
    DocumentDetailView,
    DocumentListView,
    DocumentManagementListView,
    DocumentPublishView,
    DocumentUnpublishView,
    DocumentUpdateView,
    SubjectDownloadView,
)

app_name = "document"

urlpatterns = [
    # Catalogue public
    path("", DocumentListView.as_view(), name="list"),
    path("<uuid:pk>/", DocumentDetailView.as_view(), name="detail"),

    # Fichiers contrôlés (sujet / corrigé)
    path(
        "<uuid:pk>/sujet/telecharger/",
        SubjectDownloadView.as_view(),
        name="download_subject",
    ),
    path(
        "<uuid:pk>/corrige/consulter/",
        CorrectionViewView.as_view(),
        name="view_correction",
    ),
    path(
        "<uuid:pk>/corrige/telecharger/",
        CorrectionDownloadView.as_view(),
        name="download_correction",
    ),

    # Gestion (staff / administrateurs)
    path("gerer/", DocumentManagementListView.as_view(), name="management_list"),
    path("nouveau/", DocumentCreateView.as_view(), name="create"),
    path("<uuid:pk>/modifier/", DocumentUpdateView.as_view(), name="update"),
    path("<uuid:pk>/supprimer/", DocumentDeleteView.as_view(), name="delete"),
    path("<uuid:pk>/publier/", DocumentPublishView.as_view(), name="publish"),
    path("<uuid:pk>/depublier/", DocumentUnpublishView.as_view(), name="unpublish"),
]