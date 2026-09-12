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
from gradia.utils.enums import PaymentStatus, PaymentType, OrderStatus


class PaymentWebhookService:
    """
    Contient le traitement métier commun d'un webhook de paiement.

    Cette classe ne vérifie volontairement pas encore la signature
    spécifique à Stripe ou Flutterwave.
    """

    @staticmethod
    @transaction.atomic
    def mark_payment_success(
        *,
        payment: Payment,
        provider_transaction_id: str,
        provider_response: dict,
    ) -> Payment:
        """
        Marque un paiement comme réussi après validation du webhook.

        Le montant doit avoir été vérifié avant l'appel de cette méthode.
        """

        # Vérifie qu'il s'agit bien d'une transaction principale.
        if payment.transaction_type != PaymentType.CHARGE:
            raise ValidationError(
                "Seule une transaction CHARGE peut être confirmée."
            )

        # Si le paiement est déjà réussi, on rend le traitement idempotent.
        # Un même webhook peut en effet être reçu plusieurs fois.
        if payment.status == PaymentStatus.SUCCESS:
            return payment

        # Un paiement déjà échoué, annulé ou frauduleux
        # ne doit pas être transformé arbitrairement en succès.
        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(
                "Ce paiement ne peut plus être confirmé."
            )

        # Une référence fournisseur valide est obligatoire
        # pour identifier la transaction externe.
        if not provider_transaction_id:
            raise ValidationError(
                "L'identifiant de transaction fournisseur est obligatoire."
            )

        # Enregistre l'identifiant officiel fourni par le prestataire.
        payment.provider_transaction_id = provider_transaction_id

        # Conserve la réponse brute utile du fournisseur pour audit.
        payment.provider_response = provider_response

        # Le paiement est maintenant confirmé.
        payment.status = PaymentStatus.SUCCESS

        # Enregistre la date de traitement du paiement.
        from django.utils import timezone

        payment.processed_at = timezone.now()

        # Sauvegarde uniquement les champs modifiés.
        payment.save(
            update_fields=[
                "provider_transaction_id",
                "provider_response",
                "status",
                "processed_at",
                "updated_at",
            ]
        )

        # Une transaction CHARGE réussie valide également la commande.
        payment.order.status = OrderStatus.SUCCESS

        # Sauvegarde le nouveau statut de la commande.
        payment.order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        # Retourne le paiement maintenant confirmé.
        return payment


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

        # Retourne la transaction locale ,Le paiement n'est PAS encore considéré comme réussi.
        return payment
        