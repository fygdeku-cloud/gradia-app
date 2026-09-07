"""
Vues de gestion du module Document (listes d'administration, publication).

La publication / dépublication s'effectue exclusivement via des requêtes POST
afin d'éviter toute mutation d'état par simple GET (sécurité CSRF comprise).
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView


from gradia.document.models import Document
from gradia.document.selectors import get_manageable_documents
from gradia.document.services import DocumentService
from .mixins import DocumentManageMixin


class DocumentManagementListView(DocumentManageMixin, ListView):
    """Liste de gestion des documents (publiés et non publiés)."""

    template_name = "document/document_management_list.html"
    context_object_name = "documents"
    paginate_by = 20

    def get_queryset(self):
        return get_manageable_documents()


class DocumentPublishView(DocumentManageMixin, View):
    """Publie un document (POST uniquement)."""

    def post(self, request, *args, **kwargs):
        document = get_object_or_404(Document, pk=self.kwargs.get("pk"))
        DocumentService.publish(document=document)
        messages.success(request, _("Document publié."))
        return redirect("document:management_list")


class DocumentUnpublishView(DocumentManageMixin, View):
    """Dépublic un document (POST uniquement)."""

    def post(self, request, *args, **kwargs):
        document = get_object_or_404(Document, pk=self.kwargs.get("pk"))
        DocumentService.unpublish(document=document)
        messages.success(request, _("Document dépublié."))
        return redirect("document:management_list")