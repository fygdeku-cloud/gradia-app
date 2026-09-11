from __future__ import annotations

from django.db.models import QuerySet

from gradia.payment.models import Payment
from gradia.utils.enums import PaymentStatus, PaymentType


# Retourne le queryset de base des paiements.
# le service ou la vue accède ensuite à payment.order.
def get_payments() -> QuerySet[Payment]:
    return Payment.objects.select_related("order")


# Retourne un paiement précis à partir de son UUID.
def get_payment(payment_id) -> Payment | None:
    return (
        get_payments()
        .filter(pk=payment_id)
        .first()
    )


# Retourne tous les paiements appartenant aux commandes d'un étudiant.
# On passe par order__student puisque Payment ne possède pas directement
# de relation vers User.
def get_user_payments(user) -> QuerySet[Payment]:
    return (
        get_payments()
        .filter(order__student=user)
        .order_by("-created_at")
    )


# Retourne les transactions associées à une commande précise.
# Cela permet notamment de voir les différentes tentatives de paiement
# et les éventuels remboursements liés à cette commande.
def get_order_payments(order) -> QuerySet[Payment]:
    return (
        get_payments()
        .filter(order=order)
        .order_by("-created_at")
    )


# Retourne les paiements d'une commande ayant un statut précis.
def get_order_payments_by_status(
    order,
    status: str,
) -> QuerySet[Payment]:
    return (
        get_order_payments(order)
        .filter(status=status)
    )


# Retourne le paiement CHARGE réussi d'une commande.
# On ne considère ici que la transaction financière principale de type CHARGE.
def get_successful_charge_for_order(order) -> Payment | None:
    return (
        get_order_payments(order)
        .filter(
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.SUCCESS,
        )
        .first()
    )


# Retourne le paiement CHARGE actuellement en attente pour une commande.
# Cela permettra notamment d'éviter de créer inutilement plusieurs
# transactions PENDING pour la même commande.
def get_pending_charge_for_order(order) -> Payment | None:
    return (
        get_order_payments(order)
        .filter(
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.PENDING,
        )
        .first()
    )


# Recherche un paiement grâce à la référence fournie par le prestataire.
# Cette référence va servir à faire le rapprochement entre Gradia
# et le système externe de paiement.
def get_payment_by_provider_reference(
    provider_reference: str,
) -> Payment | None:
    if not provider_reference:
        return None

    return (
        get_payments()
        .filter(provider_reference=provider_reference)
        .first()
    )


# Recherche une transaction grâce à son identifiant fournisseur.
# C'est particulièrement important pour le traitement des webhooks :
# le fournisseur envoie généralement un identifiant permettant de retrouver
# la transaction correspondante dans Gradia.
def get_payment_by_provider_transaction_id(
    provider_transaction_id: str,
) -> Payment | None:
    if not provider_transaction_id:
        return None

    return (
        get_payments()
        .filter(
            provider_transaction_id=provider_transaction_id,
        )
        .first()
    )


# Retourne les remboursements associés à une transaction CHARGE.
# parent_id permet de retrouver les transactions de remboursement
# directement liées au paiement d'origine.
def get_refunds_for_payment(
    payment: Payment,
) -> QuerySet[Payment]:
    return (
        Payment.objects
        .filter(
            parent=payment,
            transaction_type__in=[
                PaymentType.REFUND,
                PaymentType.PARTIAL_REFUND,
            ],
        )
        .select_related("order")
        .order_by("-created_at")
    )


# Retourne les transactions financières réussies.
# Les remboursements réussis sont également inclus, car ils représentent
# des opérations financières effectivement exécutées.
def get_successful_payments(
    user=None,
) -> QuerySet[Payment]:
    queryset = get_payments().filter(
        status=PaymentStatus.SUCCESS,
    )

    if user is not None:
        queryset = queryset.filter(order__student=user)

    return queryset.order_by("-created_at")


# Retourne les transactions actuellement en attente.
# Le paramètre user permet de limiter la recherche aux paiements
# appartenant aux commandes d'un étudiant.
def get_pending_payments(
    user=None,
) -> QuerySet[Payment]:
    queryset = get_payments().filter(
        status=PaymentStatus.PENDING,
    )

    if user is not None:
        queryset = queryset.filter(order__student=user)

    return queryset.order_by("-created_at")