from __future__ import annotations

import secrets

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from ..forms import UserSignupForm
from ..models import EmailVerification, StudentProfile
from utils.email import EmailUtil
from utils.otp import OtpService


class RegisterView(View):
    """Inscription d'un nouvel étudiant."""

    template_name = "users/register.html"
    form_class = UserSignupForm

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("users:profile")

        form = self.form_class()

        return render(
            request,
            self.template_name,
            {"form": form},
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("users:profile")

        form = self.form_class(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form},
            )

        user = form.save()

        StudentProfile.objects.create(
            user=user,
        )

        code = self._generate_verification_code()

        verification, _ = (
            EmailVerification.objects.get_or_create(
                user=user,
            )
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
            subject=_("Verify your email address"),
        )

        if not email_sent:
            verification.invalidate()

            messages.warning(
                request,
                _(
                    "Your account was created, "
                    "but we could not send the verification email."
                ),
            )

            return redirect("users:login")

        OtpService.start_cooldown(
            user_id=user.pk,
            purpose="email_verification",
            seconds=60,
        )

        request.session["verification_email"] = user.email

        messages.success(
            request,
            _(
                "Your account has been created. "
                "A verification code has been sent to your email."
            ),
        )

        return redirect("users:verify_email")

    @staticmethod
    def _generate_verification_code() -> str:
        """Génère un code OTP numérique à 6 chiffres."""
        return f"{secrets.randbelow(1_000_000):06d}"

