
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from django.views import View
from gradia.order.selectors import get_order_detail
from gradia.payment.forms import PaymentInitiationForm
from gradia.payment.selectors import get_payment
from ..services.stripe_service import StripePaymentService
from ..services.transaction_service import TransactionService
from ..services.payment_orchestrator import PaymentOrchestrator
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

        # Reconstruit le formulaire avec les données envoyées.
        form = PaymentInitiationForm(request.POST)

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
                
        # Crée l'orchestrateur chargé de sélectionner le provider.
        orchestrator = PaymentOrchestrator()
        checkout_url = orchestrator.initiate_payment(
            user=request.user,
            order=order,
            method=form.cleaned_data["method"],
            provider=form.cleaned_data["provider"],
        )
        
        return redirect(checkout_url)
    
    
class PaymentProcessingView(LoginRequiredMixin, View):
    """Vérifie l'état réel d'un paiement après le retour de Stripe."""

    def get(self, request, payment_id):
        # Récupère le paiement enregistré 
        payment = get_payment(payment_id)

        # si le paiement n'existe pas.
        if payment is None:
            raise Http404

        # Empêche un utilisateur d'accéder au paiement d'un autre étudiant.
        if payment.order.student_id != request.user.id:
            raise PermissionDenied


        if payment.status == PaymentStatus.SUCCESS:
            return redirect(
                "payment:success",
                payment_id=payment.pk,
            )

        # Récupère la référence de Checkout Session enregistrée.
        session_id = payment.provider_reference

        # Si la transaction Stripe ne posséde pas une Checkout Session.
        if not session_id:
            raise Http404

        # Vérifie directement l'état actuel auprès de Stripe.
        stripe_service = StripePaymentService()

        # Récupère la Checkout Session réelle.
        session = stripe_service.retrieve_checkout_session(
            session_id=session_id,
        )

        # Si Stripe confirme le paiement, on synchronise 
        if session.payment_status == "paid":
            stripe_service.validate_checkout_amount(
                session=session,
                expected_amount=payment.amount,
            )

            # Récupère la référence du PaymentIntent Stripe.
            payment_intent_id = session.payment_intent

            if not payment_intent_id:
                raise ValidationError(
                    "La transaction Stripe ne possède pas de référence de paiement."
                )

            # Marque la transaction comme réussie.
            TransactionService.mark_success(
                payment=payment,
                provider_transaction_id=payment_intent_id,
                provider_response={
                    "session_id": session.id,
                    "payment_status": session.payment_status,
                    "payment_intent": payment_intent_id,
                },
            )

            # Redirige immédiatement vers la page de succès.
            return redirect(
                "payment:success",
                payment_id=payment.pk,
            )

        # on affiche la page de traitement.
        return render(
            request,
            "payment/processing.html",
            {"payment": payment},
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
        