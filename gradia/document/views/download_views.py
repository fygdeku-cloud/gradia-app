"""
Vues contrôlées d'accès aux fichiers (sujet / corrigé).

Ces vues sont la SEULE porte d'entrée vers les fichiers des documents :
- le stockage est protégé (hors MEDIA_ROOT) : aucune URL directe n'existe ;
- chaque requête vérifie l'authentification ET l'autorisation côté serveur ;
- la consultation du corrigé (`inline`) est strictement distincte du
  téléchargement (`attachment`).
"""

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
from gradia.utils.enums import ACTION_DOWNLOAD_SUBJECT, ACTION_VIEW_CORRECTION


class _DocumentFileView(View):
    """Base commune : récupération du document et vérification d'accès."""

    access_action = None

    def _get_document(self, **kwargs):
        return get_object_or_404(Document, pk=kwargs.get("pk"))


class SubjectDownloadView(_DocumentFileView):
    """
    Téléchargement du sujet.

    Politique :
    - document gratuit publié : accessible à tous (y compris visiteur anonyme) ;
    - document payant         : réservé aux utilisateurs payeurs ;
    - staff / gestion          : accès complet.
    """

    access_action = ACTION_DOWNLOAD_SUBJECT

    def get(self, request, *args, **kwargs):
        document = self._get_document(**kwargs)
        if not DocumentAccessService.can_download_subject(request.user, document):
            raise PermissionDenied(_("Vous n'êtes pas autorisé à télécharger ce sujet."))
        response = DocumentServingService.serve_subject_download(document)
        DocumentAccessLogService.log_access(
            request.user, document, self.access_action
        )
        return response


class CorrectionViewView(_DocumentFileView):
    """
    Consultation (affichage inline) du corrigé.



    Réservée aux utilisateurs connectés ayant payé (ou document gratuit),
    ou au staff. Le fichier original n'est jamais exposé publiquement :
    il est servi par Django en `inline` depuis le stockage protégé.
    """

    access_action = ACTION_VIEW_CORRECTION

    def get(self, request, *args, **kwargs):
        document = self._get_document(**kwargs)
        if not DocumentAccessService.can_view_correction(request.user, document):
            raise PermissionDenied(
                _("Vous n'êtes pas autorisé à consulter ce corrigé. Le paiement "
                  "est requis pour les documents payants.")
            )
        response = DocumentServingService.serve_correction_inline(document)
        DocumentAccessLogService.log_access(
            request.user, document, self.access_action
        )
        return response


class CorrectionDownloadView(_DocumentFileView):
    """
    Téléchargement du corrigé — STRICTEMENT réservé à la gestion (staff).

    Les étudiants, même payeurs, ne peuvent jamais télécharger le corrigé.
    """

    def get(self, request, *args, **kwargs):
        document = self._get_document(**kwargs)
        if not DocumentAccessService.can_download_correction(request.user, document):
            raise PermissionDenied(
                _("Le téléchargement du corrigé n'est pas autorisé pour les étudiants.")
            )
        response = DocumentServingService.serve_correction_download(document)

        return response