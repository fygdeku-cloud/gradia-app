from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View

from gradia.order.selectors import get_order_detail
from gradia.payment.forms import PaymentInitiationForm
from gradia.payment.services import PaymentService


class PaymentInitiationView(LoginRequiredMixin, View):
    """
    Affiche le formulaire de paiement et initialise
    une transaction PENDING.
    """

    # URL utilisée lorsque l'utilisateur n'est pas authentifié.
    login_url = "users:login"

    def get(self, request, order_id):
        """
        Affiche le formulaire de sélection du paiement.
        """

        # Recherche la commande concernée.
        order = get_order_detail(order_id)

        # Une commande inexistante ne peut pas être payée.
        if order is None:
            raise Http404

        # Un utilisateur ne peut payer que sa propre commande.
        if order.student_id != request.user.id:
            raise PermissionDenied

        # Crée un formulaire vide pour afficher les choix disponibles.
        form = PaymentInitiationForm()

        # Affiche la page de paiement.
        return render(
            request,
            "payment/payment_form.html",
            {
                "form": form,
                "order": order,
            },
        )

    def post(self, request, order_id):
        """
        Reçoit le choix de paiement et crée la transaction locale.
        """

        # Recherche la commande côté serveur.
        order = get_order_detail(order_id)

        # Bloque une commande inexistante.
        if order is None:
            raise Http404

        # Vérifie que la commande appartient à l'utilisateur connecté.
        if order.student_id != request.user.id:
            raise PermissionDenied

        # Construit le formulaire avec les données POST.
        form = PaymentInitiationForm(request.POST)

        # Valide les choix du formulaire.
        if not form.is_valid():
            return render(
                request,
                "payment/payment_form.html",
                {
                    "form": form,
                    "order": order,
                },
                status=400,
            )

        try:
            # Le service récupère lui-même le montant officiel
            # depuis order.total_amount.
            payment = PaymentService.initiate_payment(
                user=request.user,
                order=order,
                method=form.cleaned_data["method"],
                provider=form.cleaned_data["provider"],
            )
        except ValidationError as exc:
            # Affiche les erreurs métier dans le formulaire.
            form.add_error(None, exc)

            return render(
                request,
                "payment/payment_form.html",
                {
                    "form": form,
                    "order": order,
                },
                status=400,
            )

        # La transaction reste PENDING tant que le fournisseur
        # n'a pas confirmé le paiement via son mécanisme prévu.
        return redirect(
            "payment:payment_pending",
            payment_id=payment.pk,
        )
        