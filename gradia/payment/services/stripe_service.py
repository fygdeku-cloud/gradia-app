from __future__ import annotations

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

import stripe


class StripePaymentService:
    """Gère les interactions techniques entre Gradia et Stripe."""

    def __init__(self) -> None:
        # Initialise la clé secrète Stripe configurée dans Django.
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_checkout_session(
        self,
        *,
        payment,
    ) -> tuple[str, str]:
        """Crée une Checkout Session Stripe."""

        # Récupère le montant de la transaction.
        amount = payment.amount.amount

        if amount <= 0:
            raise ValidationError(
                "Le montant du paiement doit être supérieur à zéro."
            )

        # Construit l'URL de retour après Checkout.
        success_url = (
            f"{settings.SITE_URL}"
            f"/payment/processing/{payment.pk}/"
            "?session_id={CHECKOUT_SESSION_ID}"
        )

        # Construit l'URL utilisée en cas d'annulation.
        cancel_url = (
            f"{settings.SITE_URL}"
            f"/payment/cancel/{payment.pk}/"
        )

        try:
            # Demande à Stripe de créer une Checkout Session.
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": payment.amount.currency.code.lower(),
                            "product_data": {
                                "name": f"Commande {payment.order.order_number}",
                            },
                            "unit_amount": int(amount),
                        },
                        "quantity": 1,
                    }
                ],
                metadata={
                    "payment_id": str(payment.pk),
                    "order_id": str(payment.order.pk),
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )

        # Transforme une erreur Stripe en erreur compréhensible par Django.
        except stripe.error.StripeError as exc:
            raise ValidationError(
                f"Impossible de créer le paiement Stripe : {exc}"
            ) from exc

        # Retourne l'identifiant et l'URL de la Checkout Session.
        return session.id, session.url
    # Récupère une Checkout Session directement depuis Stripe.
    
    
    def retrieve_checkout_session(self, *, session_id: str):
        """Récupère l'état réel d'une Checkout Session auprès de Stripe."""
    
        try:
            # Demande à Stripe l'état actuel de la Checkout Session.
            return stripe.checkout.Session.retrieve(session_id)
    
        except stripe.error.StripeError as exc:
            raise ValidationError(
                f"Impossible de vérifier le paiement auprès de Stripe : {exc}"
            ) from exc


    def validate_checkout_amount(self, *, session, expected_amount) -> None:
        """Vérifie le montant réellement payé par Stripe."""
    
        actual_amount = session.amount_total
    
        # Récupère le montant attendu en unités Stripe.
        expected_amount_minor = int(expected_amount.amount)
    
        # Vérifie le montant réellement reçu.
        if session.amount_total != expected_amount_minor:
            raise ValidationError(
                _("Le montant reçu par Stripe ne correspond pas au montant attendu.")
            )
        
        # Vérifie la devise attendue.
        expected_currency = expected_amount.currency.code.lower()
    
        # Vérifie la devise envoyée par Stripe.
        if session.currency != expected_currency:
            raise ValidationError(
                _("La devise du paiement Stripe ne correspond pas à celle attendue.")
            )
       
        