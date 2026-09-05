import uuid
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Otp
from .otp_utils import OtpUtils
from gradia.utils.email import EmailUtil
from gradia.utils.enums import OtpPurpose


class OtpVerificationError(ValueError):
    pass


class OtpRateLimitError(ValueError):
    pass


class OtpEmailError(ValueError):
    pass


class OtpService:
    """
    Service gérant la création et la logique métier de l'OTP.
    """

    @staticmethod
    def create(user, purpose: str) -> tuple[Otp, str]:
        if purpose not in {
            OtpPurpose.SIGNUP,
            OtpPurpose.LOGIN,
            OtpPurpose.PASSWORD_RESET,
        }:
            raise ValueError(_("Purpose OTP invalide."))

        if OtpUtils.is_on_cooldown(user.pk, purpose):
            raise OtpRateLimitError(_("Veuillez patienter avant de demander un nouveau code."))

        validity_minutes = getattr(settings, "OTP_VALID_MINUTES", 10)
        raw_code = OtpUtils.generate_code()
        expiration_at = timezone.now() + timedelta(minutes=validity_minutes)

        with transaction.atomic():
            Otp.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
            otp = Otp.objects.create(
                user=user,
                purpose=purpose,
                expiration_at=expiration_at,
            )
            otp.set_code(raw_code)
            otp.save(update_fields=["code_hash"])
            transaction.on_commit(
                lambda: OtpUtils.start_cooldown(user.pk, purpose),
            )

        otp._raw_code = raw_code
        token = OtpUtils.create_token(otp.pk, user.pk, purpose)
        return otp, token


class OtpEmailService:
    """
    Service d'envoi de l'OTP par email via EmailUtil existant
    (API unique : send_otp, synchrone, pas de Celery).
    """

    @staticmethod
    def send_otp(user, otp: Otp, template: str = "emails/users/otp_email.html") -> bool:
        raw_code = getattr(otp, "_raw_code", None)
        if not raw_code:
            raise ValueError("Le code brut de l'OTP est manquant pour l'envoi.")

        sent = EmailUtil.send_email_with_template(
            template=template,
            context={"user": user, "code": raw_code},
            receivers=[user.email],
            subject=_("Votre code de vérification")
        )
        if not sent:
            raise OtpEmailError(
                _("Le code n'a pas pu être envoyé. Vérifiez la connexion à Mailpit.")
            )
        return True


class OtpVerifyService:
    """
    Service pour la vérification du token et du code OTP fournis.
    """

    @staticmethod
    def _resolve_otp(token: str, purpose: str) -> Otp:
        try:
            otp_id, user_id, token_purpose = OtpUtils.verify_token(token)
            if token_purpose != purpose:
                raise OtpVerificationError(_("Ce token ne correspond pas à cette opération."))
        except Exception as e:
            raise OtpVerificationError(_("Le lien de vérification est invalide ou a expiré.")) from e

        try:
            return Otp.objects.select_for_update().select_related("user").get(
                pk=otp_id, user_id=user_id, purpose=purpose
            )
        except Otp.DoesNotExist as err:
            raise OtpVerificationError(_("Ce code de vérification est introuvable.")) from err

    @staticmethod
    def verify(token: str, code: str, purpose: str) -> Otp:
        verification_error = None

        with transaction.atomic():
            otp = OtpVerifyService._resolve_otp(token, purpose)
            if otp.is_used or otp.is_expired:
                raise OtpVerificationError(_("Ce code a expiré ou a déjà été utilisé. Demandez un nouveau code."))
            if not otp.can_attempt:
                raise OtpVerificationError(_("Trop de tentatives. Demandez un nouveau code."))

            if not otp.is_valid_code(code):
                otp.increment_attempts()
                verification_error = OtpVerificationError(
                    _("Le code saisi est incorrect.")
                )
            else:
                otp.mark_verified()
                OtpUtils.clear_cooldown(otp.user_id, purpose)
                # La vérification d'un OTP signup ou login confirme l'adresse email
                # (même comportement que la référence : signup + login marquent is_verified).
                if purpose in {OtpPurpose.SIGNUP, OtpPurpose.LOGIN}:
                    otp.user.email_verified = True
                    otp.user.save(update_fields=["email_verified"])

        if verification_error:
            raise verification_error

        return otp


class PasswordResetTokenService:
    """
    Service gérant le jeton d'autorisation temporaire après vérification de l'OTP
    pour la réinitialisation du mot de passe.
    """

    timeout = getattr(settings, "RESET_TOKEN_TIMEOUT", 15) * 60

    @staticmethod
    def generate(user) -> str:
        token = str(uuid.uuid4())
        cache.set(f"password_reset_token:{token}", str(user.pk), timeout=PasswordResetTokenService.timeout)
        return token

    @staticmethod
    def get_user_id(token: str) -> str | None:
        if not token:
            return None
        return cache.get(f"password_reset_token:{token}")

    @staticmethod
    def delete(token: str) -> None:
        cache.delete(f"password_reset_token:{token}")
