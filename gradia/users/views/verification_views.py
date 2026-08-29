from __future__ import annotations

import secrets

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from ..forms import (
    EmailVerificationForm,
    ResendVerificationForm
)
from ..models import EmailVerification, User
from utils.email import EmailUtil
from utils.otp import OtpService



class EmailVerificationView(View):
    """Vérification de l'adresse email avec un code OTP."""

    template_name = "users/verify_email.html"
    form_class = EmailVerificationForm

    def get(self, request):
        email = request.session.get(
            "verification_email"
        )

        if not email:
            messages.info(
                request,
                _("Please enter your email address."),
            )

            return redirect(
                "users:resend_verification"
            )

        form = self.form_class()

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "email": email,
            },
        )

    def post(self, request):
        email = request.session.get(
            "verification_email"
        )

        if not email:
            messages.error(
                request,
                _("Verification session not found."),
            )

            return redirect(
                "users:resend_verification"
            )

        form = self.form_class(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "email": email,
                },
                status=400,
            )

        try:
            user = User.objects.get(
                email__iexact=email,
            )
        except User.DoesNotExist:
            messages.error(
                request,
                _("Unable to find this account."),
            )

            return redirect(
                "users:register"
            )

        verification = getattr(
            user,
            "email_verification",
            None,
        )

        if verification is None:
            messages.error(
                request,
                _("No verification code is available."),
            )

            return redirect(
                "users:resend_verification"
            )

        if verification.is_verified:
            messages.info(
                request,
                _("Your email address is already verified."),
            )

            return redirect(
                "users:login"
            )

        if verification.is_expired:
            messages.error(
                request,
                _("This verification code has expired."),
            )

            return redirect(
                "users:resend_verification"
            )

        if verification.is_max_attempts_reached:
            messages.error(
                request,
                _("Maximum verification attempts reached."),
            )

            return redirect(
                "users:resend_verification"
            )

        is_valid = verification.verify_code(
            form.cleaned_data["code"]
        )

        if not is_valid:
            remaining_attempts = max(
                verification.DEFAULT_MAX_ATTEMPTS
                - verification.attempts,
                0,
            )

            if remaining_attempts:
                messages.error(
                    request,
                    _(
                        "Invalid verification code. "
                        "%(attempts)s attempt(s) remaining."
                    )
                    % {
                        "attempts": remaining_attempts,
                    },
                )
            else:
                messages.error(
                    request,
                    _("Maximum verification attempts reached."),
                )

            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "email": email,
                },
                status=400,
            )

        OtpService.clear_cooldown(
            user_id=user.pk,
            purpose="email_verification",
        )

        request.session.pop(
            "verification_email",
            None,
        )

        messages.success(
            request,
            _(
                "Your email address has been verified successfully."
            ),
        )

        return redirect(
            "users:login"
        )


class ResendVerificationView(View):
    """Renvoie un nouveau code de vérification."""

    template_name = "users/resend_verification.html"
    form_class = ResendVerificationForm

    def get(self, request):
        form = self.form_class()

        return render(
            request,
            self.template_name,
            {"form": form},
        )

    def post(self, request):
        form = self.form_class(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form},
                status=400,
            )

        email = form.cleaned_data["email"]

        try:
            user = User.objects.get(
                email__iexact=email,
            )
        except User.DoesNotExist:
            # Ne révèle pas si l'adresse existe.
            messages.success(
                request,
                _(
                    "If an account exists with this email, "
                    "a verification code will be sent."
                ),
            )

            return redirect(
                "users:login"
            )

        if user.email_verified:
            messages.info(
                request,
                _("This email address is already verified."),
            )

            return redirect(
                "users:login"
            )

        if OtpService.is_on_cooldown(
            user.pk,
            "email_verification",
        ):
            remaining = (
                OtpService.remaining_cooldown_seconds(
                    user.pk,
                    "email_verification",
                )
            )

            messages.warning(
                request,
                _(
                    "Please wait %(seconds)s second(s) "
                    "before requesting another code."
                )
                % {
                    "seconds": remaining,
                },
            )

            request.session[
                "verification_email"
            ] = user.email

            return redirect(
                "users:verify_email"
            )

        verification, _ = (
            EmailVerification.objects.get_or_create(
                user=user,
            )
        )

        code = (
            f"{secrets.randbelow(1_000_000):06d}"
        )

        verification.set_code(code)
        verification.save()

        email_sent = EmailUtil.send_email_with_template(
            template="emails/users/email_verification.html",
            context={
                "user": user,
                "code": code,
            },
            receivers=[user.email],
            subject=_("Your new email verification code"),
        )

        if not email_sent:
            messages.error(
                request,
                _(
                    "We could not send the verification email. "
                    "Please try again later."
                ),
            )

            return redirect(
                "users:resend_verification"
            )

        OtpService.start_cooldown(
            user_id=user.pk,
            purpose="email_verification",
            seconds=60,
        )

        request.session[
            "verification_email"
        ] = user.email

        messages.success(
            request,
            _("A new verification code has been sent."),
        )

        return redirect(
            "users:verify_email"
        )

