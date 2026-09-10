from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views import View

from gradia.payment.selectors import get_user_payments


class PaymentHistoryView(LoginRequiredMixin, View):
    """
    Affiche l'historique des transactions de l'étudiant connecté.
    """

    # URL utilisée pour les utilisateurs non authentifiés.
    login_url = "users:login"

    def get(self, request):
        """
        Récupère et affiche les paiements de l'utilisateur connecté.
        """

        # Vérifie que l'utilisateur connecté est bien un étudiant.
        if not getattr(request.user, "is_student", False):
            raise PermissionDenied

        # Le selector s'occupe exclusivement de la lecture des données.
        payments = get_user_payments(request.user)

        # Affiche l'historique des paiements.
        return render(
            request,
            "payment/history.html",
            {
                "payments": payments,
            },
        )