from __future__ import annotations

from django.core.exceptions import ValidationError
from .transaction_service import TransactionService

from .stripe_service import StripePaymentService
from gradia.payment.validators import (
    validate_order_for_payment,
    validate_payment_method_and_provider,
    validate_user_can_pay,
)


class PaymentOrchestrator:
    """Orchestre les paiements indépendamment du fournisseur utilisé."""

    def __init__(self) -> None:
        # Service Stripe utilisé lorsque le fournisseur est Stripe.
        self.stripe = StripePaymentService()

    def initiate_payment(
        self,
        *,
        user,
        order,
        method: str,
        provider: str,
    ):
        """Initialise un paiement avec le fournisseur approprié."""

        # Vérifie que l'utilisateur est autorisé à payer.
        validate_user_can_pay(user)

        # Vérifie que la commande peut être payée par cet utilisateur.
        validate_order_for_payment(order, user)

        # Vérifie la compatibilité méthode/fournisseur.
        validate_payment_method_and_provider(
            method=method,
            provider=provider,
        )

        if provider == "stripe":
            # Crée la transaction locale avant de contacter Stripe.
            payment = TransactionService.create_charge(
                order=order,
                amount=order.total_amount,
                method=method,
                provider=provider,
            )

            # Crée la Checkout Session auprès de Stripe.
            session_id, checkout_url = self.stripe.create_checkout_session(
                payment=payment,
            )

            # Conserve la référence de la Checkout Session localement.
            payment.provider_reference = session_id

            # Conserve également cette référence dans les métadonnées.
            payment.metadata = {
                **payment.metadata,
                "checkout_session_id": session_id,
            }

            # Sauvegarde les informations Stripe.
            payment.save(
                update_fields=[
                    "provider_reference",
                    "metadata",
                    "updated_at",
                ]
            )

            # Retourne la transaction et l'URL vers Stripe Checkout.
            return payment, checkout_url

        # Signale qu'aucun service n'est encore disponible pour ce provider.
        raise ValidationError(
            f"Le fournisseur de paiement « {provider} » n'est pas disponible."
        )
        