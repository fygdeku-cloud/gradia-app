from __future__ import annotations

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from gradia.payment.models import Payment
from gradia.utils.enums import OrderStatus, PaymentStatus, PaymentType


class TransactionService:
    """Centralise les opérations métier sur les transactions de paiement."""

    @staticmethod
    @transaction.atomic
    def create_charge(
        *,
        order,
        amount,
        method: str,
        provider: str,
    ) -> Payment:
        """Crée une transaction de type charge en attente."""

        return Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.PENDING,
            amount=amount,
            method=method,
            provider=provider,
        )

    @staticmethod
    @transaction.atomic
    def mark_success(
        *,
        payment: Payment,
        provider_transaction_id: str,
        provider_response: dict,
    ) -> Payment:
        """Marque une transaction comme réussie."""

        # Une transaction réussie doit être une charge.
        if payment.transaction_type != PaymentType.CHARGE:
            raise ValidationError("Seules les charges peuvent être confirmées.")

        # Une transaction déjà réussie est considérée comme idempotente.
        if payment.status == PaymentStatus.SUCCESS:
            return payment

        # Une autre transition vers SUCCESS n'est pas autorisée.
        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(
                "Cette transaction ne peut plus être confirmée."
            )

        # L'identifiant fourni par le provider est obligatoire.
        if not provider_transaction_id:
            raise ValidationError(
                "La référence de transaction du fournisseur est obligatoire."
            )

        # Met à jour les informations de la transaction.
        payment.provider_transaction_id = provider_transaction_id
        payment.provider_response = provider_response
        payment.status = PaymentStatus.SUCCESS
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
        
        payment.order.status = OrderStatus.SUCCESS
        
        payment.order.save(
           update_fields=["status", "updated_at"]
        )

        return payment

    @staticmethod
    @transaction.atomic
    def mark_failed(
        *,
        payment: Payment,
        provider_response: dict,
        failure_reason: str = "",
    ) -> Payment:
        """Marque une transaction comme échouée."""

        # Une transaction réussie ne doit jamais redevenir échouée.
        if payment.status == PaymentStatus.SUCCESS:
            return payment

        # Seules les transactions en attente peuvent échouer.
        if payment.status != PaymentStatus.PENDING:
            return payment

        # Met à jour les informations d'échec.
        payment.status = PaymentStatus.FAILED
        payment.provider_response = provider_response
        payment.failure_reason = failure_reason
        payment.processed_at = timezone.now()

        # Sauvegarde les champs modifiés.
        payment.save(
            update_fields=[
                "status",
                "provider_response",
                "failure_reason",
                "processed_at",
                "updated_at",
            ]
        )

        # Retourne la transaction mise à jour.
        return payment

    @staticmethod
    @transaction.atomic
    def mark_cancelled(
        *,
        payment: Payment,
        provider_response: dict,
        failure_reason: str = "",
    ) -> Payment:
        """Marque une transaction comme annulée."""

        # Une transaction réussie ne peut pas être annulée ici.
        if payment.status == PaymentStatus.SUCCESS:
            return payment

        # Une transaction déjà terminée ne doit pas être modifiée.
        if payment.status != PaymentStatus.PENDING:
            return payment

        # Met à jour les informations d'annulation.
        payment.status = PaymentStatus.CANCELLED
        payment.provider_response = provider_response
        payment.failure_reason = failure_reason
        payment.processed_at = timezone.now()

        # Sauvegarde les champs modifiés.
        payment.save(
            update_fields=[
                "status",
                "provider_response",
                "failure_reason",
                "processed_at",
                "updated_at",
            ]
        )

        # Retourne la transaction mise à jour.
        return payment
    
    
    @staticmethod
    @transaction.atomic
    def mark_fraud(
        *,
        payment: Payment,
        provider_response: dict,
        failure_reason: str = "",
    ) -> Payment:
        """Marque une transaction comme suspecte."""
        
        # Une transaction déjà réussie ne doit pas être marquée frauduleuse
        # par un traitement ultérieur.
        if payment.status == PaymentStatus.SUCCESS:
          return payment

        # Enregistre les informations nécessaires à l'analyse administrative.
        payment.status = PaymentStatus.FRAUD
        payment.provider_response = provider_response
        payment.failure_reason = failure_reason
        payment.processed_at = timezone.now()
    
        # Sauvegarde le nouvel état de la transaction.
        payment.save(
            update_fields=[
                "status",
                "provider_response",
                "failure_reason",
                "processed_at",
                "updated_at",
            ]
        )

        # Retourne la transaction suspecte.
        return payment
       