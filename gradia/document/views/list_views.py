"""
Vues publiques de liste du module Document.
"""

from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from gradia.document.selectors import (
    annotate_with_paid_status,
    get_published_documents,
    search_documents,
)


class DocumentListView(ListView):
    """Catalogue public des documents publiés, avec recherche."""

    template_name = "document/document_list.html"
    context_object_name = "documents"
    paginate_by = 12

    def get_queryset(self):
        queryset = get_published_documents()
        queryset = search_documents(queryset, query=self.request.GET.get("q", ""))
        return annotate_with_paid_status(queryset, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context