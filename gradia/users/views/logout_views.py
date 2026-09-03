from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View



class LogoutView(View):
    """Déconnexion de l'utilisateur."""

    def post(self, request):
        logout(request)

        messages.success(
            request,
            _("You have been logged out successfully."),
        )

        return redirect("users:login")
