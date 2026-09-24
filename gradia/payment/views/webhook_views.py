from __future__ import annotations

import json

import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View

from gradia.payment.services.webhook_service import WebhookService


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(View):

    def post(self, request: HttpRequest) -> HttpResponse:
        # Récupère le payload brut envoyé par Stripe.
        payload = request.body

        # Récupère la signature Stripe.
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        # Vérifie que Stripe a bien envoyé sa signature.
        if not signature:
            return HttpResponse(status=400)

        try:
            # Vérifie cryptographiquement la signature et construit
            # l'événement Stripe.
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )

            # Transforme le payload vérifié en dictionnaire JSON.
            payload_data = json.loads(payload.decode("utf-8"))

        except (
            ValueError,
            stripe.error.SignatureVerificationError,
        ):
            # Payload invalide ou signature invalide.
            return HttpResponse(status=400)

        # Récupère l'adresse IP directe de la requête.
        remote_address = request.META.get("REMOTE_ADDR")

        # Délègue toute la logique métier au service.
        WebhookService().process_event(
            event=event,
            payload=payload_data,
            signature=signature,
            remote_address=remote_address,
        )

        # Stripe a reçu une réponse positive.
        return HttpResponse(status=200)