from __future__ import annotations

import secrets
from uuid import UUID

from django.conf import settings
from django.core.cache import caches
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner


otp_cache = caches["otp"]


class OtpUtils:
    """
    Utilitaires techniques pour la gestion des OTP.

    Responsabilités :
    - génération sécurisée des codes OTP ;
    - gestion du cooldown ;
    - création de tokens signés ;
    - vérification des tokens signés.

    La logique métier de l'authentification est gérée
    dans services.py.
    """

    SIGNER_SALT = "gradia.users.otp"

    signer = TimestampSigner(
        salt=SIGNER_SALT,
    )

    # ==========================================================
    # OTP
    # ==========================================================

    @staticmethod
    def generate_code() -> str:
        """
        Génère un code OTP numérique cryptographiquement aléatoire.

        Exemple :
            "583021"
        """

        maximum = 10 ** settings.OTP_LENGTH

        code = secrets.randbelow(maximum)

        return f"{code:0{settings.OTP_LENGTH}d}"

    # ==========================================================
    # COOLDOWN
    # ==========================================================

    @staticmethod
    def get_cooldown_key(
        user_id: int,
        purpose: str,
    ) -> str:
        """
        Génère la clé de cache utilisée pour le cooldown OTP.
        """

        return f"otp:cooldown:{purpose}:{user_id}"

    @classmethod
    def start_cooldown(
        cls,
        user_id: int,
        purpose: str,
    ) -> None:
        """
        Active le cooldown après une demande d'OTP.
        """

        key = cls.get_cooldown_key(
            user_id=user_id,
            purpose=purpose,
        )

        otp_cache.set(
            key,
            True,
            timeout=settings.OTP_COOLDOWN_SECONDS,
        )

    @classmethod
    def is_on_cooldown(
        cls,
        user_id: int,
        purpose: str,
    ) -> bool:
        """
        Vérifie si l'utilisateur est encore soumis
        au cooldown pour ce type d'OTP.
        """

        key = cls.get_cooldown_key(
            user_id=user_id,
            purpose=purpose,
        )

        return otp_cache.get(key) is not None

    @classmethod
    def clear_cooldown(
        cls,
        user_id: int,
        purpose: str,
    ) -> None:
        """
        Supprime le cooldown d'un utilisateur.
        """

        key = cls.get_cooldown_key(
            user_id=user_id,
            purpose=purpose,
        )

        otp_cache.delete(key)

    # ==========================================================
    # TOKEN SIGNÉ
    # ==========================================================

    @classmethod
    def create_token(
        cls,
        otp_id: UUID,
        user_id: UUID,
        purpose: str,
    ) -> str:
        """
        Crée un token signé contenant les informations
        permettant d'identifier l'opération OTP.

        Le token ne contient jamais le code OTP en clair.
        """

        payload = (
            f"{otp_id}:"
            f"{user_id}:"
            f"{purpose}"
        )

        return cls.signer.sign(payload)

    @classmethod
    def verify_token(
        cls,
        token: str,
    ) -> tuple[UUID, UUID, str]:
        """
        Vérifie un token signé et retourne :

            (otp_id, user_id, purpose)

        Raises:
            SignatureExpired:
                si le token a dépassé sa durée de validité.

            BadSignature:
                si le token est invalide ou a été falsifié.
        """

        payload = cls.signer.unsign(
            token,
            max_age=settings.OTP_TOKEN_MAX_AGE_SECONDS,
        )

        try:
            otp_id, user_id, purpose = payload.split(
                ":",
                maxsplit=2,
            )

            return (
                UUID(otp_id),
                UUID(user_id),
                purpose,
            )

        except (ValueError, TypeError) as exc:
            raise BadSignature(
                "Invalid OTP token payload."
            ) from exc

    @classmethod
    def is_token_expired(
        cls,
        token: str,
    ) -> bool:
        """
        Vérifie si un token OTP est expiré.

        Retourne :
            True  → token expiré
            False → token valide ou signature invalide
        """

        try:
            cls.signer.unsign(
                token,
                max_age=settings.OTP_TOKEN_MAX_AGE_SECONDS,
            )

        except SignatureExpired:
            return True

        except BadSignature:
            return False

        return False