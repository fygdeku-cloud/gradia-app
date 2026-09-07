"""Vues du module Document (initialisées depuis les fichiers spécialisés)."""

from gradia.document.views.detail_views import DocumentDetailView
from gradia.document.views.download_views import (
    CorrectionDownloadView,
    CorrectionViewView,
    SubjectDownloadView,
)
from gradia.document.views.list_views import DocumentListView
from gradia.document.views.management_views import (
    DocumentManagementListView,
    DocumentPublishView,
    DocumentUnpublishView,
)
from gradia.document.views.upload_views import (
    DocumentCreateView,
    DocumentDeleteView,
    DocumentUpdateView,
)

__all__ = [
    "CorrectionDownloadView",
    "CorrectionViewView",
    "DocumentCreateView",
    "DocumentDeleteView",
    "DocumentDetailView",
    "DocumentListView",
    "DocumentManagementListView",
    "DocumentPublishView",
    "DocumentUnpublishView",
    "DocumentUpdateView",
    "SubjectDownloadView",
]