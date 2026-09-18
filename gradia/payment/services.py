from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import stripe
from django.conf import settings

from gradia.payment.models import Payment
from gradia.payment.selectors import get_pending_charge_for_order
from gradia.payment.validators import (
    validate_order_for_payment,
    validate_payment_method_and_provider,
    validate_user_can_pay,
)
from gradia.utils.enums import PaymentStatus, PaymentType, OrderStatus


        
class PaymentWebhookService:
    """Contient la logique métier des événements Stripe."""

    @staticmethod
    @transaction.atomic
    def handle_checkout_session_completed(*, checkout_session: dict) -> Payment:
        """
        Traite un Checkout Session Stripe confirmé.
        """
        # Récupère les métadonnées que PaymentService avait placées dans la Checkout Session.
        metadata = checkout_session.get("metadata") or {}
        # Récupère notre identifiant de paiement local.
        payment_id = metadata.get("payment_id")

        if not payment_id:
            raise ValidationError(
                "Le webhook Stripe ne contient aucun identifiant de paiement."
            )

        try:
            # Recherche la transaction locale correspondant exactement au paiement Stripe.
            payment = Payment.objects.select_for_update().get(
                pk=payment_id,
            )

        except Payment.DoesNotExist as exc:
            # Le webhook ne doit jamais créer un paiement Gradia 
            raise ValidationError(
                "Le paiement Gradia correspondant est introuvable."
            ) from exc

        # Vérifie que la transaction attend bien une confirmation.
        if payment.transaction_type != PaymentType.CHARGE:
            raise ValidationError(
                "Une transaction non-CHARGE ne peut pas être confirmée."
            )

        # Vérifie que cette transaction provient bien de Stripe.
        if payment.provider != "stripe":
            raise ValidationError(
                "Le fournisseur du paiement ne correspond pas à Stripe."
            )

        # Vérifie que la Checkout Session reçue correspond à celle
        # enregistrée lors de l'initialisation du paiement.
        checkout_session_id = checkout_session.get("id")

        if not checkout_session_id:
            raise ValidationError(
                "L'identifiant de Checkout Session est absent."
            )

        if payment.provider_reference != checkout_session_id:
            raise ValidationError(
                "La Checkout Session Stripe ne correspond pas au paiement."
            )

        # Si le paiement a déjà été confirmé,le webhook est maintenant comme un retraitement idempotent.
        if payment.status == PaymentStatus.SUCCESS:
            return payment

        # Un paiement qui n'est plus PENDING ne doit pas être confirmé une seconde fois.
        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(
                "Ce paiement ne peut plus être confirmé."
            )

        # Récupère le montant total réellement indiqué par Stripe.
        stripe_amount = checkout_session.get("amount_total")

        # Le montant Stripe doit exister.
        if stripe_amount is None:
            raise ValidationError(
                "Le montant Stripe est absent."
            )

        # Convertit le montant local en unité mineure Stripe.
        expected_amount = int(payment.amount.amount)

        # Vérifie que Stripe a bien traité le montant attendu.
        if stripe_amount != expected_amount:
            raise ValidationError(
                "Le montant du paiement Stripe ne correspond pas "
                "au montant attendu."
            )

        # Vérifie la devise.
        stripe_currency = (
            checkout_session.get("currency") or ""
        ).lower()

        if stripe_currency != "xaf":
            raise ValidationError(
                "La devise du paiement Stripe est incorrecte."
            )

        # Stripe indique que la session est payée.
        payment_status = checkout_session.get("payment_status")

        if payment_status != "paid":
            raise ValidationError(
                "La Checkout Session Stripe n'est pas marquée comme payée."
            )

        # Récupère l'identifiant du PaymentIntent Stripe.
        payment_intent_id = checkout_session.get("payment_intent")

        if not payment_intent_id:
            raise ValidationError(
                "L'identifiant PaymentIntent Stripe est absent."
            )

        # Finalise la transaction locale.
        return PaymentWebhookService.mark_payment_success(
            payment=payment,
            provider_transaction_id=str(payment_intent_id),
            provider_response=checkout_session,
        )


    @staticmethod
    @transaction.atomic
    def mark_payment_success(
        *,
        payment: Payment,
        provider_transaction_id: str,
        provider_response: dict,
    ) -> Payment:
        """Marque une transaction locale comme réussie."""

        # Une transaction REFUND ne peut pas être transformée en CHARGE réussi.
        if payment.transaction_type != PaymentType.CHARGE:
            raise ValidationError(
                "Seule une transaction CHARGE peut être confirmée."
            )

        # Rend le traitement idempotent si Stripe renvoie le même événement.
        if payment.status == PaymentStatus.SUCCESS:
            return payment

        # Seul un paiement en attente peut devenir SUCCESS.
        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(
                "Ce paiement ne peut plus être confirmé."
            )

        # L'identifiant Stripe est obligatoire.
        if not provider_transaction_id:
            raise ValidationError(
                "L'identifiant de transaction fournisseur est obligatoire."
            )

        # Enregistre l'identifiant PaymentIntent Stripe.
        payment.provider_transaction_id = provider_transaction_id

        # Conserve la réponse Stripe vérifiée pour le suivi technique.
        payment.provider_response = provider_response

        # Change l'état local du paiement.
        payment.status = PaymentStatus.SUCCESS

        # Enregistre la date de confirmation.
        payment.processed_at = timezone.now()

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

        # Sauvegarde le nouvel état de la commande.
        payment.order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return payment
    
    
    @staticmethod
    @transaction.atomic
    def mark_payment_failed(
        *,
        payment: Payment,
        status: str,
        provider_response: dict,
        failure_reason: str = "",
    ) -> Payment:
        """
        Termine un paiement Stripe sans le considérer comme réussi car Le paiement doit encore être PENDING.
        """

        # Seules les transactions CHARGE peuvent représenter le paiement de la commande.
        if payment.transaction_type != PaymentType.CHARGE:
            raise ValidationError(
                "Seule une transaction CHARGE peut être mise en échec."
            )

        # Un paiement déjà confirmé ne doit jamais être rétrogradé.
        if payment.status == PaymentStatus.SUCCESS:
            return payment

        # Un paiement déjà terminé ne doit pas être retraité.
        if payment.status != PaymentStatus.PENDING:
            return payment

        # Vérifie que le nouveau statut appartient bien aux états utilisés pour terminer un paiement sans succès.
        if status not in {
            PaymentStatus.FAILED,
            PaymentStatus.CANCELLED,
        }:
            raise ValidationError(
                "Statut de paiement invalide."
            )

        # Enregistre la réponse Stripe vérifiée.
        payment.provider_response = provider_response

        # Enregistre le motif lorsqu'il est fourni.
        payment.failure_reason = failure_reason

        payment.status = status

        payment.processed_at = timezone.now()

        # Sauvegarde les champs modifiés.
        payment.save(
            update_fields=[
                "provider_response",
                "failure_reason",
                "status",
                "processed_at",
                "updated_at",
            ]
        )

        # La commande reste PENDING afin que l'étudiant puisse effectuer une nouvelle tentative de paiement.
        return payment
    
    
    @staticmethod
    @transaction.atomic
    def handle_checkout_session_expired(
        *,
        checkout_session: dict,
    ) -> Payment:
        """Traite l'expiration d'une Checkout Session Stripe."""

        # Récupère les métadonnées de notre Checkout Session.
        metadata = checkout_session.get("metadata") or {}

        # Payment local est identifié par cette valeur.
        payment_id = metadata.get("payment_id")

        # Une session sans identifiant local ne peut pas être associée à une transaction 
        if not payment_id:
            raise ValidationError(
                "Le webhook Stripe ne contient aucun identifiant de paiement."
            )

        try:
            # Verrouille la ligne pendant le traitement afin d'éviter deux traitements concurrents du même paiement.
            payment = Payment.objects.select_for_update().get(
                pk=payment_id,
            )

        except Payment.DoesNotExist as exc:
            # Refuse l'événement s'il ne correspond à aucun paiement local.
            raise ValidationError(
                "Le paiement Gradia correspondant est introuvable."
            ) from exc

        # Vérifie que le paiement appartient bien à Stripe.
        if payment.provider != "stripe":
            raise ValidationError(
                "Le fournisseur du paiement ne correspond pas à Stripe."
            )

        # Vérifie l'identifiant de la Checkout Session.
        checkout_session_id = checkout_session.get("id")

        if payment.provider_reference != checkout_session_id:
            raise ValidationError(
                "La Checkout Session Stripe ne correspond pas au paiement."
            )

        # Marque le paiement comme annulé.
        return PaymentWebhookService.mark_payment_failed(
            payment=payment,
            status=PaymentStatus.CANCELLED,
            provider_response=checkout_session,
            failure_reason="La Checkout Session Stripe a expiré.",
        )
        
        
    @staticmethod
    @transaction.atomic
    def handle_checkout_session_failed(
        *,
        checkout_session: dict,
    ) -> Payment:
        """Traite l'échec asynchrone d'une Checkout Session Stripe."""

        # Récupère les métadonnées de la session.
        metadata = checkout_session.get("metadata") or {}

        # Récupère notre identifiant de paiement local.
        payment_id = metadata.get("payment_id")

        # Refuse un événement impossible à rattacher 
        if not payment_id:
            raise ValidationError(
                "Le webhook Stripe ne contient aucun identifiant de paiement."
            )

        try:
            payment = Payment.objects.select_for_update().get(
                pk=payment_id,
            )

        except Payment.DoesNotExist as exc:
            
            raise ValidationError(
                "Le paiement Gradia correspondant est introuvable."
            ) from exc

        # Vérifie le fournisseur attendu.
        if payment.provider != "stripe":
            raise ValidationError(
                "Le fournisseur du paiement ne correspond pas à Stripe."
            )

        # Vérifie que la session reçue est bien celle enregistrée.
        checkout_session_id = checkout_session.get("id")

        if payment.provider_reference != checkout_session_id:
            raise ValidationError(
                "La Checkout Session Stripe ne correspond pas au paiement."
            )

        # Marque le paiement comme échoué.
        return PaymentWebhookService.mark_payment_failed(
            payment=payment,
            status=PaymentStatus.FAILED,
            provider_response=checkout_session,
            failure_reason="Le paiement Stripe a échoué.",
        )
        
        
        
class PaymentService:
    """Contient la logique métier liée à l'initialisation d'un paiement."""

    @staticmethod
    @transaction.atomic
    def initiate_payment(
        *,
        user,
        order,
        method: str,
        provider: str,
    ) -> tuple[Payment, str]:
        # Crée le paiement local puis une session Stripe Checkout.

        # Vérifie que l'utilisateur est autorisé à effectuer un paiement.
        validate_user_can_pay(user)

        # Vérifie que la commande appartient à l'utilisateur et
        # qu'elle est dans un état permettant le paiement.
        validate_order_for_payment(order, user)

        # Vérifie la compatibilité entre le moyen de paiement
        # et le fournisseur sélectionné.
        validate_payment_method_and_provider(
            method=method,
            provider=provider,
        )

        # Stripe ne doit être utilisé que pour les paiements par carte
        # avec le fournisseur Stripe.
        if provider != "stripe":
            raise ValidationError(
                "Ce service de paiement utilise actuellement Stripe."
            )

        # Récupère le montant total de la commande.
        amount = order.total_amount

        # Empêche l'envoi d'un montant négatif à Stripe.
        if amount < 0:
            raise ValidationError(
                "Le montant de la commande ne peut pas être négatif."
            )

        #  le montant doit être converti en unité monétaire mineure.
        stripe_amount = int(amount.amount)

        # ne permet pas de créer un paiement réel de montant nul.
        if stripe_amount == 0:
            raise ValidationError(
                "Une commande d'un montant nul ne nécessite pas de paiement Stripe."
            )

        # Création de la transaction locale.
        payment = Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.PENDING,
            amount=amount,
            method=method,
            provider=provider,
            metadata={
                # Ces identifiants utilent au webhook Stripe
                "order_id": str(order.pk),
            },
        )

        try:
            # Configure le SDK Stripe avec la clé secrète déjà présente dans les paramètres Django.
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Crée la page de paiement hébergée par Stripe.
            checkout_session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "xaf",
                            "product_data": {
                                "name": f"Commande {order.order_number}",
                            },
                            "unit_amount": stripe_amount,
                        },
                        "quantity": 1,
                    }
                ],
                metadata={
                    # Identifiant de notre paiement local.
                    "payment_id": str(payment.pk),

                    # Identifiant de notre commande locale.
                    "order_id": str(order.pk),
                },
                # URL appelée par Stripe après un paiement.
                success_url=(
                    f"{settings.SITE_URL}"
                    f"/payment/processing/{payment.pk}/"
                    "? session_id={CHECKOUT_SESSION_ID}"
                ),
                # URL appelée lorsque l'utilisateur annule le paiement.
                cancel_url=(
                    f"{settings.SITE_URL}"
                    f"/payment/cancel/{payment.pk}/"
                )
            )

        except stripe.error.StripeError as exc:
            # Le paiement local reste dans la transaction atomique
            raise ValidationError(
                "Impossible de créer la session de paiement Stripe."
            ) from exc

        # Conserve l'identifiant unique de la Checkout Session Stripe.
        payment.provider_reference = checkout_session.id

        # Conserve également les informations utiles au diagnostic et au traitement ultérieur du webhook.
        payment.metadata = {
            **payment.metadata,
            "checkout_session_id": checkout_session.id,
        }

        # Sauvegarde uniquement les champs modifiés.
        payment.save(
            update_fields=[
                "provider_reference",
                "metadata",
                "updated_at",
            ]
        )

        return payment, checkout_session.url