        
"""
Services de sécurité de Gradia.

Ce module fournit :
- la récupération de l'adresse IP ;
- le throttling des connexions ;
- le verrouillage temporaire après plusieurs échecs ;
- la journalisation des événements de sécurité.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import caches
from django.http import HttpRequest


security_cache = caches["security"]

security_logger = logging.getLogger(
    "security"
)


def get_client_ip(
    request: HttpRequest,
) -> str:
    """Retourne l'adresse IP du client."""

    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR"
    )

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get(
        "REMOTE_ADDR",
        "",
    )


class LoginThrottle:
    """Gestion du verrouillage temporaire des connexions."""

    @staticmethod
    def _key(
        identifier: str,
    ) -> str:
        return (
            f"login:attempts:"
            f"{identifier.lower().strip()}"
        )

    @classmethod
    def is_locked(
        cls,
        identifier: str,
    ) -> bool:
        """Indique si l'identifiant est temporairement bloqué."""

        attempts = security_cache.get(
            cls._key(identifier),
            0,
        )

        return attempts >= settings.LOGIN_MAX_ATTEMPTS

    @classmethod
    def remaining_lockout_seconds(
        cls,
        identifier: str,
    ) -> int:
        """Retourne le temps restant du verrouillage."""

        ttl = security_cache.ttl(
            cls._key(identifier)
        )

        return max(
            int(ttl or 0),
            0,
        )

    @classmethod
    def register_failure(
        cls,
        identifier: str,
    ) -> int:
        """Enregistre une tentative de connexion échouée."""

        key = cls._key(identifier)

        attempts = (
            security_cache.get(
                key,
                0,
            )
            + 1
        )

        security_cache.set(
            key,
            attempts,
            timeout=(
                settings.LOGIN_LOCKOUT_MINUTES
                * 60
            ),
        )

        return attempts

    @classmethod
    def reset(
        cls,
        identifier: str,
    ) -> None:
        """Réinitialise le compteur après succès."""

        security_cache.delete(
            cls._key(identifier)
        )


def log_security_event(
    request: HttpRequest | None,
    event_type: str,
    *,
    user=None,
    email: str = "",
    metadata: dict | None = None,
) -> None:
    """Journalise un événement de sécurité."""

    from core.models import SecurityEventLog

    ip_address = (
        get_client_ip(request)
        if request
        else ""
    )

    user_agent = (
        request.META.get(
            "HTTP_USER_AGENT",
            "",
        )
        if request
        else ""
    )

    resolved_email = (
        email
        or (
            user.email
            if user
            and hasattr(user, "email")
            else ""
        )
    )

    security_logger.info(
        "event=%s user=%s email=%s ip=%s",
        event_type,
        user,
        resolved_email,
        ip_address,
    )

    SecurityEventLog.objects.create(
        user=(
            user
            if user
            and user.is_authenticated
            else None
        ),
        email=resolved_email,
        event_type=event_type,
        ip_address=ip_address or None,
        user_agent=user_agent,
        metadata=metadata or {},
    )
    