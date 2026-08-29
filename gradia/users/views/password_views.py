from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from ..forms import (
    PasswordResetRequestForm,
    SetNewPasswordForm,
)
from ..models import User


class PasswordResetRequestView(View):
    """
    Demande de réinitialisation du mot de passe.

    La logique complète de réinitialisation sera ajoutée
    lorsque le mécanisme de token/OTP correspondant sera défini.
    """

    template_name = "users/password_reset.html"
    form_class = PasswordResetRequestForm

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

        user = User.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()

        if user:
            # Le mécanisme d'envoi sera branché ici
            # après création du système de reset.
            pass

        messages.success(
            request,
            _(
                "If an account exists with this email, "
                "you will receive instructions to reset your password."
            ),
        )

        return redirect(
            "users:login"
        )


class PasswordResetConfirmView(View):
    """Confirmation du nouveau mot de passe."""

    template_name = "users/password_reset_confirm.html"
    form_class = SetNewPasswordForm

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

        messages.info(
            request,
            _(
                "The password reset mechanism is not configured yet."
            ),
        )

        return redirect(
            "users:login"
        )