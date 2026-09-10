from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from gradia.payment.models import Payment
from gradia.payment.selectors import get_pending_charge_for_order
from gradia.payment.validators import (
    validate_order_for_payment,
    validate_payment_method_and_provider,
    validate_user_can_pay,
)
from gradia.utils.enums import PaymentStatus, PaymentType


class PaymentService:
    """
    Contient la logique métier liée à l'initiation d'un paiement.
    
    Le service ne fait pas encore appel directement à Stripe ou Flutterwave.
    Cette partie sera ajoutée lorsque nous implémenterons l'adaptateur
    du fournisseur de paiement.
    """

    @staticmethod
    @transaction.atomic
    def initiate_payment(*, user, order, method: str, provider: str) -> Payment:
        """
        Crée une transaction de paiement PENDING pour une commande.

        Le montant utilisé est toujours celui de la commande.
        Le montant envoyé éventuellement par le navigateur n'est jamais
        considéré comme une source de vérité.
        """

        # Vérifie que l'utilisateur est authentifié et qu'il est étudiant.
        validate_user_can_pay(user)

        # Vérifie que la commande appartient bien à l'utilisateur,
        # qu'elle est encore payable et que son montant est valide.
        validate_order_for_payment(order, user)

        # Vérifie que le moyen de paiement correspond bien
        # au fournisseur sélectionné.
        validate_payment_method_and_provider(method, provider)

        # Recherche une transaction CHARGE encore en attente
        # pour éviter de créer inutilement plusieurs paiements PENDING.
        existing_payment = get_pending_charge_for_order(order)

        # Si une tentative de paiement est déjà en attente,
        # on la réutilise au lieu de créer une deuxième transaction.
        if existing_payment is not None:
            return existing_payment

        # Crée la transaction locale avec le montant officiel
        # provenant de la commande.
        payment = Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.PENDING,
            amount=order.total_amount,
            method=method,
            provider=provider,
        )

        # Retourne la transaction locale.
        # Le paiement n'est PAS encore considéré comme réussi.
        return payment
        