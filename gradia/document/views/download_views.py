from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views import View

from gradia.document.models import Document
from gradia.document.services import (
    DocumentAccessLogService,
    DocumentAccessService,
    DocumentServingService,
)
from gradia.utils.enums import (
    ACTION_DOWNLOAD_SUBJECT,
    ACTION_VIEW_CORRECTION,
)


class _DocumentFileView(View):
    """Base commune : récupération du document."""

    access_action = None

    def _get_document(self, **kwargs):
        return get_object_or_404(Document, pk=kwargs.get("pk"))


class SubjectDownloadView(_DocumentFileView):
    """
    Téléchargement du sujet.

    - document gratuit publié : accessible aux visiteurs ;
    - document payant : accessible aux utilisateurs autorisés ;
    - gestion : accès complet.
    """

    access_action = ACTION_DOWNLOAD_SUBJECT

    def get(self, request, *args, **kwargs):
        document = self._get_document(**kwargs)

        if not DocumentAccessService.can_download_subject(
            request.user,
            document,
        ):
            raise PermissionDenied(
                _("Vous n'êtes pas autorisé à télécharger ce sujet.")
            )

        response = DocumentServingService.serve_subject_download(
            user=request.user,
            document=document,
        )

        DocumentAccessLogService.log_access(
            request.user,
            document,
            self.access_action,
        )

        return response


class CorrectionViewView(_DocumentFileView):
    """
    Consultation du corrigé uniquement.

    Le corrigé est affiché dans le navigateur.
    Aucun téléchargement du corrigé n'est proposé par cette vue.
    """

    access_action = ACTION_VIEW_CORRECTION

    def get(self, request, *args, **kwargs):
        document = self._get_document(**kwargs)

        if not DocumentAccessService.can_view_correction(
            request.user,
            document,
        ):
            raise PermissionDenied(
                _(
                    "Vous n'êtes pas autorisé à consulter ce corrigé. "
                    "Le paiement est requis pour les documents payants."
                )
            )

        response = DocumentServingService.serve_correction_inline(
            user=request.user,
            document=document,
        )

        DocumentAccessLogService.log_access(
            request.user,
            document,
            self.access_action,
        )

        return response