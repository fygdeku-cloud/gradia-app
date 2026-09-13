
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from django.views import View
from gradia.order.selectors import get_order_detail
from gradia.payment.forms import PaymentInitiationForm
from gradia.payment.services import PaymentService
from gradia.payment.selectors import get_payment
from gradia.utils.enums import PaymentStatus



class PaymentInitiationView(LoginRequiredMixin, View):
    """Affiche le formulaire puis démarre le paiement Stripe."""

    # Les utilisateurs non authentifiés sont redirigés vers la connexion.
    login_url = "users:login"

    def get(self, request, order_id):
        """Affiche le formulaire de choix du moyen de paiement."""

        # Récupère la commande via le sélecteur existant.
        order = get_order_detail(order_id)

        # Une commande inexistante retourne une 404.
        if order is None:
            raise Http404

        # Un étudiant ne peut payer que sa propre commande.
        if order.student_id != request.user.id:
            raise PermissionDenied

        # Initialise le formulaire vide.
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
        """Valide le formulaire et redirige vers Stripe Checkout."""

        # Récupère la commande via le sélecteur existant.
        order = get_order_detail(order_id)

        # Une commande inexistante retourne une 404.
        if order is None:
            raise Http404

        # Empêche un utilisateur de payer la commande d'un autre étudiant.
        if order.student_id != request.user.id:
            raise PermissionDenied

        # Reconstruit le formulaire avec les données envoyées.
        form = PaymentInitiationForm(request.POST)

        # Si le formulaire est invalide, on réaffiche la page
        # avec les erreurs correspondantes.
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
            # Le service crée le Payment local puis la session Stripe.
            checkout_url = PaymentService.initiate_payment(
                user=request.user,
                order=order,
                method=form.cleaned_data["method"],
                provider=form.cleaned_data["provider"],
            )

        except ValidationError as exc:
            form.add_error(None, exc)

            # Réaffiche le formulaire sans masquer l'erreur.
            return render(
                request,
                "payment/payment_form.html",
                {
                    "form": form,
                    "order": order,
                },
                status=400,
            )

        # Redirige directement l'étudiant vers Stripe Checkout.
        return redirect(checkout_url)
    
    
    
class PaymentProcessingView(LoginRequiredMixin, View):
    """
    Affiche la page d'attente après le retour depuis Stripe.
    Elle attend que le webhook Stripe mette à jour la base locale.
    """

    login_url = "users:login"

    def get(self, request, payment_id):
        """Affiche la page de vérification du paiement."""

        # Récupère le paiement via le sélecteur existant.
        payment = get_payment(payment_id)

        # Si le paiement n'existe pas, retourner une 404.
        if payment is None:
            raise Http404

        # Un étudiant ne peut consulter que son propre paiement.
        if payment.order.student_id != request.user.id:
            raise PermissionDenied

        # Affiche la page de traitement.
        return render(
            request,
            "payment/processing.html",
            {
                "payment": payment,
            },
        )


class PaymentStatusView(LoginRequiredMixin, View):
    """
    Retourne le statut local du paiement.
    Cette vue est interrogée périodiquement par la page processing.
    Elle ne contacte pas Stripe et ne confirme aucun paiement.
    """

    login_url = "users:login"

    def get(self, request, payment_id):
        """Retourne le statut courant du paiement."""

        # Récupère le paiement via le sélecteur existant.
        payment = get_payment(payment_id)

        # Ne révèle pas l'existence d'un paiement inexistant.
        if payment is None:
            raise Http404

        # Empêche un utilisateur de consulter le paiement
        # appartenant à un autre étudiant.
        if payment.order.student_id != request.user.id:
            raise PermissionDenied

        # Retourne uniquement les informations nécessaires au frontend.
        return JsonResponse(
            {
                "status": payment.status,
                "payment_id": str(payment.pk),
            }
        )
        
        
# Vue affichée uniquement lorsque le paiement a réellement été confirmé.
class PaymentSuccessView(LoginRequiredMixin, View):
    def get(self, request, payment_id):
        # Récupère le paiement demandé.
        payment = get_payment(payment_id)

        # Retourne une erreur 404 si le paiement n'existe pas.
        if payment is None:
            raise Http404

        # Vérifie que le paiement appartient bien à l'utilisateur connecté.
        if payment.order.student_id != request.user.id:
            raise PermissionDenied

        # Un paiement non confirmé ne peut pas afficher la page de succès.
        if payment.status != PaymentStatus.SUCCESS:
            return redirect(
                "payment:processing",
                payment_id=payment.pk,
            )

        return render(
            request,
            "payment/success.html",
            {"payment": payment},
        )


# Vue affichée lorsque l'utilisateur quitte ou annule le paiement.
class PaymentCancelView(LoginRequiredMixin, View):
    def get(self, request, payment_id):
        # Récupère le paiement demandé.
        payment = get_payment(payment_id)

        # Retourne une erreur 404 si le paiement n'existe pas.
        if payment is None:
            raise Http404

        # Vérifie que le paiement appartient bien à l'utilisateur connecté.
        if payment.order.student_id != request.user.id:
            raise PermissionDenied

        # Si le paiement est finalement réussi, on ne doit pas afficher
        # une page d'annulation.
        if payment.status == PaymentStatus.SUCCESS:
            return redirect(
                "payment:success",
                payment_id=payment.pk,
            )

        # Affiche la page d'annulation.
        return render(
            request,
            "payment/cancel.html",
            {"payment": payment},
        )
        