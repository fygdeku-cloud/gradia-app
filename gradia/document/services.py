"""
Logique métier du module Document.

Responsabilités :
- création, modification, publication/dépublication, suppression ;
- autorisation d'accès centralisée (consultation / téléchargement) ;
- journalisation des accès ;
- service contrôlé des fichiers (consultation et téléchargement).

Les opérations multi-écritures sont enveloppées dans des transactions.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import File
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.utils.translation import gettext_lazy as _

from gradia.document.models import Document, DocumentAccessLog
from gradia.document.selectors import has_confirmed_payment
from gradia.utils.enums import ACTION_DOWNLOAD_SUBJECT, ACTION_VIEW_CORRECTION


class DocumentService:
    """Opérations métier sur les documents."""

    @staticmethod
    @transaction.atomic
    def create(*, form) -> Document:
        """
        Crée un document à partir d'un formulaire validé.

        Le formulaire apporte les fichiers (sujet/corrigé) après les validations
        métier (extension, MIME, signature, taille, nom de fichier).
        """
        if not form.is_valid():
            raise ValidationError(_("Le formulaire de création est invalide."))
        try:
            return form.save()
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(_("Impossible de créer le document.")) from exc

    @staticmethod
    @transaction.atomic
    def update(*, document: Document, form) -> Document:
        """
        Met à jour un document (métadonnées et fichiers optionnels).

        L'opération est atomique : aucun état intermédiaire n'est observable
        entre la validation et l'enregistrement.
        """
        if not form.is_valid():
            raise ValidationError(_("Le formulaire de modification est invalide."))

        try:
            instance = form.save(commit=False)

            subject_file = form.cleaned_data.get("subject_file")
            correction_file = form.cleaned_data.get("correction_file")

            if subject_file is None:
                instance.subject_file = document.subject_file
            else:
                if document.subject_file and document.subject_file.name:
                    document.subject_file.field.storage.delete(document.subject_file.name)
                instance.subject_file = subject_file

            if correction_file is None:
                instance.correction_file = document.correction_file
            else:
                if document.correction_file and document.correction_file.name:
                    document.correction_file.field.storage.delete(document.correction_file.name)
                instance.correction_file = correction_file

            instance.save()
            return instance
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(_("Impossible de modifier le document.")) from exc

    @staticmethod
    @transaction.atomic
    def delete(*, document: Document) -> None:
        """Supprime un document et ses fichiers associés."""
        storage = document.subject_file.field.storage
        subject_name = document.subject_file.name
        correction_name = document.correction_file.name
        document.delete()
        for file_name in (subject_name, correction_name):
            if file_name:
                storage.delete(file_name)

    @staticmethod
    @transaction.atomic
    def publish(*, document: Document) -> Document:
        """Publie un document (le rend visible du catalogue et accessible)."""
        if document.is_published:
            return document
        document.is_published = True
        document.save(update_fields=["is_published", "updated_at"])
        return document

    @staticmethod
    @transaction.atomic
    def unpublish(*, document: Document) -> Document:
        """Dépublic un document : immédiatement retiré du catalogue public."""
        if not document.is_published:
            return document
        document.is_published = False
        document.save(update_fields=["is_published", "updated_at"])
        return document
class DocumentAccessService:
    """
    Autorisations d'accès centralisées pour les documents.

    Toute vue qui expose un fichier (sujet ou corrigé) DOIT vérifier ses droits
    via ce service. Les règles ne sont jamais dupliquées dans les vues.

    Politique :
    - SUJET   : téléchargeable si le document est publié et (gratuit OU payé) ;
    - CORRIGÉ : consultable si le document est publié et (gratuit OU payé) ;
                jamais téléchargeable par les étudiants(consultation seule) ;
    - STAFF   : accès complet (consultation + téléchargement) en gestion.

    """

    @staticmethod
    def _is_manager(user) -> bool:
        if user is None or not user.is_authenticated:
            return False
        # is_admin est le flag métier dédié à la gestion dans le projet.
        return bool(user.is_staff or user.is_superuser or user.is_admin)

    @staticmethod
    def _can_access_document(user, document: Document) -> bool:
        """Accès au contenu (sujet et corrigé) pour un document donné."""
        if not document.is_published and not DocumentAccessService._is_manager(user):
            return False
        if DocumentAccessService._is_manager(user):
            return True
        return has_confirmed_payment(user, document)

    @staticmethod
    def can_view_document(user, document: Document) -> bool:
        """
        L'utilisateur peut-il voir les métadonnées du document ?

        Métadonnées = catalogue (titre, description, prix, session…).
        """
        if document.is_published:
            return True
        return DocumentAccessService._is_manager(user)

    @staticmethod
    def can_download_subject(user, document: Document) -> bool:
        """L'utilisateur peut-il télécharger le fichier du sujet ?"""
        if not document.subject_file:
            return False
        if not document.is_published and not DocumentAccessService._is_manager(user):
            return False
        if not user or not user.is_authenticated:
            # Visiteur anonyme : autorisé uniquement pour les documents gratuits.

            return document.price <= 0 and document.is_published
        return DocumentAccessService._can_access_document(user, document)

    @staticmethod
    def can_view_correction(user, document: Document) -> bool:
        """
        L'utilisateur peut-il CONSULTER le corrigé ?

        Consulter ≠ télécharger. Le paiement donne un droit de consultation,
        jamais un droit de téléchargement (document payant).
        """
        if not document.has_correction():
            return False
        if not document.is_published and not DocumentAccessService._is_manager(user):
            return False
        if DocumentAccessService._is_manager(user):
            return True
        # La consultation d'un corrigé nécessite une session authentifiée.

        if not user or not user.is_authenticated:
            return False
        return has_confirmed_payment(user, document)

    @staticmethod
    def can_download_correction(user, document: Document) -> bool:
        """
        L'utilisateur peut-il TÉLÉCHARGER le corrigé ?

        Strictement réservé à la gestion(staff / administrateurs).
        Les étudiants — y compris ceux ayant payé — ne téléchargent jamais
        le corrigé original.
        """
        if not document.has_correction():
            return False
        return DocumentAccessService._is_manager(user)

    @staticmethod
    def can_manage_document(user, document: Document | None = None) -> bool:
        """L'utilisateur peut-il créer / modifier / publier / supprimer ?"""
        return DocumentAccessService._is_manager(user)

class DocumentServingService:
    # Ouvre un fichier protégé depuis le stockage configuré.
    @staticmethod
    def _open_protected_file(document_field: File) -> File:
        # Refuse immédiatement l'accès si aucun fichier n'est disponible.
        if not document_field:
            raise PermissionDenied(_("Fichier indisponible."))

        # Ouvre le fichier uniquement après que la méthode appelante
        # a effectué son contrôle d'autorisation.
        return document_field.open("rb")

    @staticmethod
    def _stream_file(
        *,
        document: Document,
        field: File,
        as_attachment: bool,
    ) -> HttpResponse:
        file_obj = DocumentServingService._open_protected_file(field)
        filename = Path(field.name).name or "document"
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        response = FileResponse(
            file_obj,
            content_type=content_type,
            as_attachment=as_attachment,
            filename=filename,
        )
        # En-têtes de sécurité supplémentaires.
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "no-store, private, max-age=0"
        response["Pragma"] = "no-cache"
        return response

      # Sert le sujet après avoir obligatoirement vérifié le droit
    # de téléchargement de l'utilisateur.
    @staticmethod
    def serve_subject_download(*, user, document: Document) -> HttpResponse:
        # Le contrôle d'accès est maintenant imposé par le service.
        if not DocumentAccessService.can_download_subject(user, document):
            raise PermissionDenied(
                _("Vous n'êtes pas autorisé à télécharger ce sujet.")
            )

        # Ouvre le fichier uniquement après autorisation.
        return DocumentServingService._stream_file(
            document=document,
            field=document.subject_file,
            as_attachment=True,
        )

    # Sert le corrigé en consultation intégrée après vérification
    # obligatoire du droit de consultation.
    @staticmethod
    def serve_correction_inline(*, user, document: Document) -> HttpResponse:
        # Le contrôle d'accès au corrigé est imposé par le service.
        if not DocumentAccessService.can_view_correction(user, document):
            raise PermissionDenied(
                _("Vous n'êtes pas autorisé à consulter ce corrigé.")
            )

        # Le fichier est envoyé au navigateur sans mode téléchargement.
        return DocumentServingService._stream_file(
            document=document,
            field=document.correction_file,
            as_attachment=False,
        )

class DocumentAccessLogService:
    """Journalisation des accès aux documents."""

    @staticmethod
    @transaction.atomic
    def log_access(
        user,
        document: Document,
        action: str,
    ) -> DocumentAccessLog:
        """Enregistre une action d'accès (consultation / téléchargement)."""
        return DocumentAccessLog.objects.create(
            user=user if user and user.is_authenticated else None,
            document=document,
            action=action,
        )