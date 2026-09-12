        
from __future__ import annotations

import json
import logging

import stripe
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from gradia.payment.services import PaymentWebhookService
from gradia.payment.models import Payment

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(View):
    """
    Point d'entrée générique pour les webhooks des fournisseurs.
    """

    def post(self, request):
        """
        Reçoit une notification serveur-à-serveur du fournisseur (Stripe).
        """
        payload = request.body
        sig_header = request.headers.get("Stripe-Signature")
        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET is not configured.")
            return JsonResponse({"detail": "Configuration error."}, status=500)

        if not sig_header:
            return JsonResponse({"detail": "Missing Stripe-Signature header."}, status=400)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            return JsonResponse({"detail": "Invalid payload."}, status=400)
        except stripe.error.SignatureVerificationError:
            return JsonResponse({"detail": "Invalid signature."}, status=400)

        # Traitement des événements
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            self._handle_checkout_session_completed(session)
        else:
            logger.info(f"Unhandled event type: {event['type']}")

        return HttpResponse(status=200)

    def _handle_checkout_session_completed(self, session):
        """
        Traite l'événement checkout.session.completed.
        """
        # Récupération de l'ID de paiement (à adapter selon votre implémentation)
        # Supposons que vous stockez l'ID du paiement dans client_reference_id
        # ou dans les métadonnées.
        payment_id = session.get("client_reference_id")
        
        if not payment_id:
            logger.error(f"No payment ID found in session: {session.get('id')}")
            return

        try:
            payment = Payment.objects.get(pk=payment_id)
        except Payment.DoesNotExist:
            logger.error(f"Payment not found: {payment_id}")
            return

        # Utilisation du service pour marquer le succès
        PaymentWebhookService.mark_payment_success(
            payment=payment,
            provider_transaction_id=session.get("payment_intent"),
            provider_response=session,
        )
        logger.info(f"Payment {payment_id} marked as success.")