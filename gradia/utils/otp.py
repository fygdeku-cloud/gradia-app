"""
Services de gestion du throttling OTP.

Le code OTP reste stocké en base de données via le modèle OtpCode.
Redis est utilisé uniquement pour les mécanismes temporaires :
- cooldown lors du renvoi d'un OTP ;
- limitation des demandes répétées.
"""

from __future__ import annotations

from django.core.cache import caches


otp_cache = caches["otp"]


class OtpService:
    """Gestion du cooldown des demandes OTP."""

    @staticmethod
    def _cooldown_key(user_id, purpose: str) -> str:
        return f"otp:cooldown:{purpose}:{user_id}"

    @classmethod
    def is_on_cooldown(
        cls,
        user_id,
        purpose: str,
    ) -> bool:
        """Retourne True si l'utilisateur est encore en cooldown."""
        return (
            otp_cache.get(
                cls._cooldown_key(user_id, purpose)
            )
            is not None
        )

    @classmethod
    def remaining_cooldown_seconds(
        cls,
        user_id,
        purpose: str,
    ) -> int:
        """Retourne le nombre de secondes restantes."""
        ttl = otp_cache.ttl(
            cls._cooldown_key(user_id, purpose)
        )

        return max(int(ttl or 0), 0)

    @classmethod
    def start_cooldown(
        cls,
        user_id,
        purpose: str,
        seconds: int,
    ) -> None:
        """Démarre le cooldown après l'envoi effectif de l'OTP."""
        otp_cache.set(
            cls._cooldown_key(user_id, purpose),
            True,
            timeout=seconds,
        )

    @classmethod
    def clear_cooldown(
        cls,
        user_id,
        purpose: str,
    ) -> None:
        """Supprime le cooldown."""
        otp_cache.delete(
            cls._cooldown_key(user_id, purpose)
        )
        
        