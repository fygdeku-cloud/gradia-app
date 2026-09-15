from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View

from gradia.payment.models import Payment, PaymentWebhookEvent
from gradia.payment.services.stripe_service import StripePaymentService
from gradia.payment.services.transaction_service import TransactionService
from gradia.utils.enums import PaymentProvider, PaymentStatus


class WebhookService(LoginRequiredMixin, View):
    """Orchestre le traitement des événements envoyés par Stripe."""

    def __init__(self) -> None:
        self.stripe = StripePaymentService()

    @transaction.atomic
    def process_event(
        self,
        *,
        event: dict,
        payload: dict,
        signature: str,
        remote_address: str | None,
    ) -> PaymentWebhookEvent:
        """Enregistre puis traite un événement Stripe de manière idempotente."""

        # Récupère les informations principales de l'événement.
        event_id = event["id"]
        event_type = event["type"]

        # Récupère ou crée le journal de l'événement.
        webhook_event, created = PaymentWebhookEvent.objects.get_or_create(
            provider=PaymentProvider.STRIPE,
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "payload": payload,
                "signature": signature,
                "remote_address": remote_address,
            },
        )

        # Si l'événement a déjà été traité, on ne le traite jamais une
        # seconde fois.
        if (
            not created
            and webhook_event.processing_status
            == PaymentWebhookEvent.ProcessingStatus.PROCESSED
        ):
            return webhook_event

        # Met l'événement en cours de traitement.
        webhook_event.processing_status = (
            PaymentWebhookEvent.ProcessingStatus.PROCESSING
        )
        webhook_event.error_message = ""
        webhook_event.save(
            update_fields=[
                "processing_status",
                "error_message",
                "updated_at",
            ]
        )

        try:
            # Sélectionne explicitement le handler correspondant à
            # l'événement Stripe.
            self._dispatch(event)

            # Le traitement est terminé.
            webhook_event.processing_status = (
                PaymentWebhookEvent.ProcessingStatus.PROCESSED
            )
            webhook_event.processed_at = timezone.now()

            webhook_event.save(
                update_fields=[
                    "processing_status",
                    "processed_at",
                    "updated_at",
                ]
            )

            return webhook_event

        except Exception as exc:
            # Conserve l'erreur pour permettre son diagnostic.
            webhook_event.processing_status = (
                PaymentWebhookEvent.ProcessingStatus.FAILED
            )
            webhook_event.error_message = str(exc)
            webhook_event.processed_at = timezone.now()

            webhook_event.save(
                update_fields=[
                    "processing_status",
                    "error_message",
                    "processed_at",
                    "updated_at",
                ]
            )

            raise

    def _dispatch(self, event: dict) -> None:
        """Sélectionne le handler correspondant au type d'événement."""

        # Récupère le type Stripe.
        event_type = event["type"]

        # Sélectionne le handler adapté.
        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "checkout.session.expired": self._handle_checkout_expired,
            "checkout.session.async_payment_failed": (
                self._handle_async_payment_failed
            ),
            "checkout.session.async_payment_succeeded": (
                self._handle_async_payment_succeeded
            ),
        }

        handler = handlers.get(event_type)

        if handler is None:
            return

        # Exécute le handler.
        handler(event["data"]["object"])

    @transaction.atomic
    def _handle_checkout_completed(self, session: dict) -> Payment:
        """Traite un paiement Checkout terminé."""

        # Récupère l'identifiant Gradia placé dans les metadata Stripe.
        payment_id = session.get("metadata", {}).get("payment_id")

        if not payment_id:
            raise ValidationError(
                _("La transaction Gradia est absente des métadonnées Stripe.")
            )

        # Verrouille la transaction afin d'éviter deux traitements concurrents.
        payment = Payment.objects.select_for_update().get(
            pk=payment_id
        )

        # Vérifie que la transaction appartient bien à Stripe.
        if payment.provider != PaymentProvider.STRIPE:
            raise ValidationError(
                _("Le fournisseur de paiement de cette transaction est invalide.")
            )

        # Vérifie que la Checkout Session correspond à celle créée pour cette transaction.
        if payment.provider_reference != session["id"]:
            raise ValidationError(
                _("La Checkout Session Stripe ne correspond pas à la transaction.")
            )

        # Une transaction déjà réussie est idempotente.
        if payment.status == PaymentStatus.SUCCESS:
            return payment

        # on interroge directement Stripe.
        verified_session = self.stripe.retrieve_checkout_session(
            session_id=session["id"]
        )

        # Stripe doit confirmer que le paiement est réellement payé.
        if verified_session.payment_status != "paid":
            raise ValidationError(
                _("Stripe ne confirme pas encore le paiement.")
            )

        try:
            # Vérifie le montant et la devise.
            self.stripe.validate_checkout_amount(
                session=verified_session,
                expected_amount=payment.amount,
            )

        except ValidationError as exc:
            # Une différence de montant est traitée comme une suspicion de fraude plutôt qu'une simple erreur technique.
            return TransactionService.mark_fraud(
                payment=payment,
                provider_response={
                    "session_id": verified_session.id,
                    "payment_status": verified_session.payment_status,
                    "amount_total": verified_session.amount_total,
                    "currency": verified_session.currency,
                },
                failure_reason=str(exc),
            )

        # Récupère l'identifiant du PaymentIntent Stripe.
        payment_intent_id = verified_session.payment_intent

        if not payment_intent_id:
            raise ValidationError(
                _("La transaction Stripe ne possède pas de référence de paiement.")
            )

        # Confirme définitivement la transaction.
        return TransactionService.mark_success(
            payment=payment,
            provider_transaction_id=payment_intent_id,
            provider_response={
                "session_id": verified_session.id,
                "payment_status": verified_session.payment_status,
                "payment_intent": payment_intent_id,
                "amount_total": verified_session.amount_total,
                "currency": verified_session.currency,
            },
        )

    @transaction.atomic
    def _handle_checkout_expired(self, session: dict) -> Payment:
        """Traite l'expiration d'une Checkout Session."""

        # Recherche la transaction depuis les metadata.
        payment_id = session.get("metadata", {}).get("payment_id")

        if not payment_id:
            raise ValidationError(
                _("La transaction Gradia est absente des métadonnées Stripe.")
            )

        # Verrouille la transaction.
        payment = Payment.objects.select_for_update().get(
            pk=payment_id
        )

        # Marque la tentative comme annulée.
        return TransactionService.mark_cancelled(
            payment=payment,
            provider_response={
                "session_id": session["id"],
                "status": session.get("status"),
            },
            failure_reason=_("La session de paiement Stripe a expiré."),
        )

    @transaction.atomic
    def _handle_async_payment_failed(self, session: dict) -> Payment:
        """Traite l'échec d'un paiement asynchrone."""

        # Récupère l'identifiant 
        payment_id = session.get("metadata", {}).get("payment_id")

        if not payment_id:
            raise ValidationError(
                _("La transaction Gradia est absente des métadonnées Stripe.")
            )

        # Verrouille la transaction.
        payment = Payment.objects.select_for_update().get(
            pk=payment_id
        )

        # Enregistre l'échec.
        return TransactionService.mark_failed(
            payment=payment,
            provider_response={
                "session_id": session["id"],
                "payment_status": session.get("payment_status"),
            },
            failure_reason=_("Le paiement asynchrone Stripe a échoué."),
        )

    def _handle_async_payment_succeeded(self, session: dict) -> Payment:
        """Traite la réussite d'un paiement asynchrone."""

        return self._handle_checkout_completed(session)
        
    