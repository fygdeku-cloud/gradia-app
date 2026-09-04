"""
Vues publiques de détail du module Document.
"""

from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from gradia.document.selectors import (
    get_document_detail,
    get_published_document_detail,
)
from gradia.document.services import DocumentAccessService


class DocumentDetailView(DetailView):
    """Détail public d'un document et de ses accès (selon les droits)."""

    template_name = "document/document_detail.html"
    context_object_name = "document"
    slug_url_kwarg = "pk"
    slug_field = "pk"

    def get_object(self, queryset=None):
        document = get_published_document_detail(self.kwargs.get("pk"))
        if document is None and not DocumentAccessService.can_manage_document(
            self.request.user
        ):
            raise Http404(_("Aucun document ne correspond à cette adresse."))
        if document is None:
            document = get_document_detail(self.kwargs.get("pk"))
        if document is None:
            raise Http404(_("Aucun document ne correspond à cette adresse."))
        return document

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["can_view_correction"] = DocumentAccessService.can_view_correction(
            user, self.object
        )
        context["can_download_subject"] = DocumentAccessService.can_download_subject(
            user, self.object
        )
        context["can_manage"] = DocumentAccessService.can_manage_document(
            user, self.object
        )
        return context