"""
Vues de création, modification et suppression de documents (gestion).
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView, DeleteView, UpdateView


from gradia.document.forms import DocumentCreateForm, DocumentUpdateForm
from gradia.document.models import Document
from .mixins import DocumentManageMixin
from gradia.document.services import DocumentAccessService, DocumentService


class DocumentCreateView(DocumentManageMixin, CreateView):
    """Création d'un document."""

    model = Document
    form_class = DocumentCreateForm
    template_name = "document/document_form.html"

    def form_valid(self, form):
        try:
            self.object = DocumentService.create(form=form)
            
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        
        messages.success(self.request, _("Document créé avec succès."))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.object.get_absolute_url()


class DocumentUpdateView(DocumentManageMixin, UpdateView):
    """Modification d'un document."""

    model = Document
    form_class = DocumentUpdateForm
    template_name = "document/document_form.html"

    def form_valid(self, form):
        try:
            self.object = DocumentService.update(document=self.object, form=form)
                
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
            
        messages.success(self.request, _("Document modifié avec succès."))
        return redirect(self.get_success_url())
    

    def get_success_url(self):
        return self.object.get_absolute_url()


class DocumentDeleteView(DocumentManageMixin, DeleteView):
    """Suppression d'un document."""

    model = Document
    template_name = "document/document_confirm_delete.html"
    success_url = reverse_lazy("document:list")

    def form_valid(self, form):
        DocumentService.delete(document=self.object)
                
        messages.success(self.request, _("Document supprimé."))
        return redirect(self.get_success_url())
    