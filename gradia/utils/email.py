       
"""
Utilitaires d'envoi d'emails pour Gradia.

Ce module centralise :
- l'envoi d'emails HTML ;
- l'envoi d'emails texte ;
- le rendu des templates ;
- la traduction des sujets ;
- le contexte global du site ;
- les pièces jointes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import translation


logger = logging.getLogger(__name__)


class EmailUtil:
    """Services utilitaires d'envoi des emails Gradia."""

    @staticmethod
    def _resolve_subject(subject: str | object) -> str:
        """Convertit proprement un sujet en chaîne de caractères."""
        if isinstance(subject, str):
            return subject

        try:
            return str(subject)
        except Exception as exc:
            logger.warning(
                "Impossible de convertir le sujet : %s",
                exc,
            )
            return ""

    @staticmethod
    def _translate_subject(
        subject: str | object,
        language: str,
    ) -> str:
        """Résout le sujet dans la langue demandée."""
        if not subject:
            return ""

        try:
            with translation.override(language):
                return str(subject)
        except Exception as exc:
            logger.warning(
                "Impossible de traduire le sujet en %s : %s",
                language,
                exc,
            )
            return str(subject)

    @staticmethod
    def _add_site_context(
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Ajoute les informations générales de Gradia aux templates."""

        context = dict(context)

        site_url = getattr(
            settings,
            "BASE_URL",
            "",
        )

        site_name = getattr(
            settings,
            "SITE_NAME",
            "Gradia",
        )

        context["site_url"] = site_url
        context["site_name"] = site_name

        return context

    @staticmethod
    def send_generic_email(
        subject: str,
        to: list[str],
        from_email: str | None = None,
        file_path: str | None = None,
        html_content: str | None = None,
        text_content: str | None = None,
    ) -> bool:
        """Envoie un email générique."""

        if not isinstance(to, list):
            raise TypeError(
                "Le paramètre 'to' doit être une liste."
            )

        if not to or any(not email for email in to):
            raise ValueError(
                "La liste des destinataires est invalide."
            )

        if not subject:
            raise ValueError(
                "Le sujet de l'email est obligatoire."
            )

        if not html_content and not text_content:
            raise ValueError(
                "Le contenu de l'email est obligatoire."
            )

        if getattr(settings, "DEBUG", False):
            subject = f"[TEST] {subject}"

        default_from = getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            "noreply@gradia.local",
        )

        sender = from_email or default_from

        if getattr(settings, "TESTING", False):
            logger.info(
                "Email ignoré : mode TESTING actif."
            )
            return True

        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content or "",
                from_email=sender,
                to=to,
            )

            if html_content:
                email.attach_alternative(
                    html_content,
                    "text/html",
                )

            if file_path:
                path = Path(file_path)

                if path.exists():
                    email.attach_file(path)
                else:
                    logger.warning(
                        "Pièce jointe introuvable : %s",
                        file_path,
                    )

            email.send()

        except Exception:
            logger.exception(
                "Erreur lors de l'envoi de l'email."
            )
            return False

        return True

    @staticmethod
    def send_email_with_template(
        template: str,
        context: dict[str, Any],
        receivers: list[str],
        subject: str | object,
        language: str | None = None,
    ) -> bool:
        """Rend un template puis envoie l'email."""

        context = EmailUtil._add_site_context(
            context
        )

        if language:
            resolved_subject = (
                EmailUtil._translate_subject(
                    subject,
                    language,
                )
            )
        else:
            resolved_subject = (
                EmailUtil._resolve_subject(subject)
            )

        context["subject"] = resolved_subject

        current_language = translation.get_language()

        try:
            if language:
                translation.activate(language)

            html_content = render_to_string(
                template_name=template,
                context=context,
            )

        except Exception:
            logger.exception(
                "Erreur lors du rendu du template email : %s",
                template,
            )
            return False

        finally:
            if current_language:
                translation.activate(
                    current_language
                )
            else:
                translation.deactivate()

        return EmailUtil.send_generic_email(
            subject=resolved_subject,
            to=receivers,
            html_content=html_content,
        )

    @staticmethod
    def send_email_with_template_batch(
        template: str,
        receivers_with_language: list[dict[str, Any]],
        subject: str | object,
    ) -> dict[str, Any]:
        """Envoie un template à plusieurs destinataires."""

        success_count = 0
        failure_count = 0
        results: list[dict[str, Any]] = []

        for recipient in receivers_with_language:
            email = recipient.get("email")

            if not email:
                failure_count += 1

                results.append(
                    {
                        "email": None,
                        "success": False,
                    }
                )

                continue

            language = (
                recipient.get("language")
                or settings.LANGUAGE_CODE
            )

            success = (
                EmailUtil.send_email_with_template(
                    template=template,
                    context=recipient.get(
                        "context",
                        {},
                    ),
                    receivers=[email],
                    subject=subject,
                    language=language,
                )
            )

            if success:
                success_count += 1
            else:
                failure_count += 1

            results.append(
                {
                    "email": email,
                    "language": language,
                    "success": success,
                }
            )

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
        }
        
        