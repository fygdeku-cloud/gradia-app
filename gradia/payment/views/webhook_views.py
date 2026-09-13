from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views import View
import stripe

from gradia.payment.services import PaymentWebhookService


class PaymentWebhookView(View):
    """
    Reçoit et vérifie les événements envoyés par Stripe.

    Cette vue ne nécessite pas d'authentification Django :
    Stripe ne possède pas de session utilisateur Django.
    """

    authentication_required = False

    def post(self, request):
        """Traite un événement Stripe envoyé par webhook."""

        # Le corps brut permettra de  vérifier correctement la signature Stripe.
        payload = request.body

        # Récupère la signature envoyée par Stripe dans l'en-tête HTTP.
        signature = request.META.get("HTTP_STRIPE_SIGNATURE")

        if not payload or not signature:
            return JsonResponse(
                {
                    "error": "Webhook Stripe invalide.",
                },
                status=400,
            )

        try:
            # Vérifie cryptographiquement la signature Stripe et construit
            # l'événement uniquement si le payload est authentique.
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )

        # Signature invalide ou payload falsifié.
        except stripe.error.SignatureVerificationError:
            return JsonResponse(
                {
                    "error": "Signature Stripe invalide.",
                },
                status=400,
            )

        # Payload qui ne peut pas être interprété comme événement Stripe.
        except ValueError:
            return JsonResponse(
                {
                    "error": "Payload Stripe invalide.",
                },
                status=400,
            )

        # Récupère le type de l'événement Stripe.
        event_type = event["type"]

        # Récupère l'objet Stripe associé à l'événement.
        event_object = event["data"]["object"]

       # Une Checkout Session terminée doit être traitée uniquement
        # lorsque Stripe indique réellement que le paiement est payé.
        if event_type == "checkout.session.completed":
            try:
                # Traite et vérifie le paiement côté serveur.
                PaymentWebhookService.handle_checkout_session_completed(
                    checkout_session=event_object,
                )

            except Exception:
                # L'erreur doit remonter afin que Stripe puisse
                # retenter la livraison du webhook.
                raise

        elif event_type == "checkout.session.expired":
            try:
                # Récupère le paiement correspondant à la session Stripe
                # puis le termine comme CANCELLED.
                PaymentWebhookService.handle_checkout_session_expired(
                    checkout_session=event_object,
                )

            except Exception:
                raise

        elif event_type == "checkout.session.async_payment_failed":
            try:
                # Termine le paiement comme FAILED.
                PaymentWebhookService.handle_checkout_session_failed(
                    checkout_session=event_object,
                )

            except Exception:
                # Stripe pourra ainsi effectuer une nouvelle livraison.
                raise

        return HttpResponse(status=200)
        