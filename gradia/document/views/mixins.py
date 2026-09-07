
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from gradia.document.services import DocumentAccessService




class DocumentManageMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("users:login")

    def test_func(self):
        return DocumentAccessService.can_manage_document(self.request.user)

