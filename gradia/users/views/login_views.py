from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from ..forms import UserLoginForm
from utils.security import LoginThrottle


class LoginView(View):
    """Connexion d'un utilisateur avec son adresse email."""

    template_name = "users/login.html"
    form_class = UserLoginForm

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("users:profile")

        form = self.form_class(request=request)

        return render(
            request,
            self.template_name,
            {"form": form},
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("users:profile")

        form = self.form_class(
            request=request,
            data=request.POST,
        )

        identifier = request.POST.get(
            "username",
            "",
        ).strip().lower()

        if identifier and LoginThrottle.is_locked(
            identifier
        ):
            remaining = (
                LoginThrottle.remaining_lockout_seconds(
                    identifier
                )
            )

            minutes = max(
                remaining // 60,
                1,
            )

            messages.error(
                request,
                _(
                    "Too many failed login attempts. "
                    "Please try again in %(minutes)s minute(s)."
                )
                % {"minutes": minutes},
            )

            return render(
                request,
                self.template_name,
                {"form": form},
                status=429,
            )

        if not form.is_valid():
            if identifier:
                LoginThrottle.register_failure(
                    identifier
                )

            return render(
                request,
                self.template_name,
                {"form": form},
                status=400,
            )

        user = form.get_user()

        if not user.is_active:
            messages.error(
                request,
                _("This account is inactive."),
            )

            return render(
                request,
                self.template_name,
                {"form": form},
                status=403,
            )

        if not user.email_verified:
            request.session["verification_email"] = (
                user.email
            )

            messages.warning(
                request,
                _(
                    "Please verify your email address "
                    "before logging in."
                ),
            )

            return redirect(
                "users:verify_email"
            )

        LoginThrottle.reset(
            identifier
        )

        login(
            request,
            user,
        )

        return redirect(
            "users:profile"
        )