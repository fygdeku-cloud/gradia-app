from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from ..forms import (
    PasswordResetRequestForm,
    SetNewPasswordForm,
    EmailVerificationForm,
)
from ..models import User
from ..services import (
    OtpEmailService,
    OtpRateLimitError,
    OtpService,
    OtpVerificationError,
    OtpVerifyService,
    PasswordResetTokenService,
)
from gradia.utils.enums import OtpPurpose


class PasswordResetRequestView(FormView):
    """Demande de réinitialisation du mot de passe."""

    template_name = "users/password_reset.html"
    form_class = PasswordResetRequestForm

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if user:
            try:
                with transaction.atomic():
                    otp, token = OtpService.create(
                        user=user,
                        purpose=OtpPurpose.PASSWORD_RESET,
                    )
                    OtpEmailService.send_otp(
                        user=user,
                        otp=otp,
                        template="emails/users/password_reset_otp.html",
                    )
                messages.info(self.request, _("Un code de réinitialisation vous a été envoyé."))
                url = reverse("users:password_reset_otp")
                return redirect(f"{url}?token={token}")
            except OtpRateLimitError:
                messages.info(
                    self.request,
                    _(
                        "Si un compte existe avec cette adresse, "
                        "vous recevrez les instructions nécessaires."
                    ),
                )

        messages.success(
            self.request,
            _(
                "If an account exists with this email, "
                "you will receive instructions to reset your password."
            ),
        )
        return redirect("users:login")


class PasswordResetOtpView(FormView):
    """Vérification de l'OTP pour réinitialiser le mot de passe."""
    template_name = "users/verify_password_reset.html"
    form_class = EmailVerificationForm

    def get_initial(self):
        return {"token": self.request.GET.get("token")}

    def form_valid(self, form):
        token = form.cleaned_data.get("token")
        code = form.cleaned_data.get("code")

        try:
            otp = OtpVerifyService.verify(token=token, code=code, purpose=OtpPurpose.PASSWORD_RESET)

            # Authorization successful, create a short-lived token for password change
            reset_token = PasswordResetTokenService.generate(otp.user)

            messages.success(self.request, _("OTP verified. You can now reset your password."))
            url = reverse("users:password_reset_confirm")
            return redirect(f"{url}?token={reset_token}")

        except OtpVerificationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class PasswordResetConfirmView(FormView):
    """Confirmation du nouveau mot de passe."""

    template_name = "users/password_reset_confirm.html"
    form_class = SetNewPasswordForm

    def dispatch(self, request, *args, **kwargs):
        self.token = request.GET.get("token") or request.POST.get("token")
        if not self.token or not PasswordResetTokenService.get_user_id(self.token):
            messages.error(request, _("The password reset link is invalid or has expired."))
            return redirect("users:password_reset")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {"token": self.token}

    def form_valid(self, form):
        user_id = PasswordResetTokenService.get_user_id(form.cleaned_data["token"])
        user = User.objects.get(pk=user_id)
        user.set_password(form.cleaned_data["password1"])
        # La réinitialisation confirme la possession de l'adresse email
        # (même comportement que la référence : is_verified devient True).
        user.email_verified = True
        user.save(update_fields=["password", "email_verified"])

        PasswordResetTokenService.delete(form.cleaned_data["token"])

        messages.success(self.request, _("Your password has been successfully reset. You can now login."))
        return redirect("users:login")