from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from gradia.utils.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    PaymentType,
)


def validate_user_can_pay(user) -> None:
    if not user or not user.is_authenticated:
        raise ValidationError(
            _("Vous devez être authentifié pour effectuer un paiement.")
        )

    if not getattr(user, "is_student", False):
        raise ValidationError(
            _("Seuls les étudiants peuvent effectuer un paiement.")
        )


def validate_order_for_payment(order, user) -> None:
    if order is None:
        raise ValidationError(
            _("La commande est introuvable.")
        )

    if order.student_id != user.id:
        raise ValidationError(
            _("Vous n'êtes pas autorisé à payer cette commande.")
        )

    if order.status != OrderStatus.PENDING:
        raise ValidationError(
            _("Cette commande ne peut plus être payée.")
        )

    if order.total_amount.amount <= 0:
        raise ValidationError(
            _("Le montant de la commande doit être supérieur à zéro.")
        )


def validate_payment_method_and_provider(
    method: str,
    provider: str,
) -> None:
    if (
        method == PaymentMethod.CARD
        and provider != PaymentProvider.STRIPE
    ):
        raise ValidationError(
            _("Le paiement par carte doit utiliser Stripe.")
        )

    if (
        method == PaymentMethod.MOBILE_MONEY
        and provider != PaymentProvider.FLUTTERWAVE_MOBILE_MONEY
    ):
        raise ValidationError(
            _("Le paiement Mobile Money doit utiliser Flutterwave.")
        )


def validate_payment_amount(amount, order) -> None:
    if amount is None:
        raise ValidationError(
            _("Le montant du paiement est obligatoire.")
        )

    if amount != order.total_amount:
        raise ValidationError(
            _("Le montant du paiement ne correspond pas au montant de la commande.")
        )


def validate_provider_transaction_id(transaction_id: str) -> None:
    if not transaction_id:
        raise ValidationError(
            _("La référence de transaction du fournisseur est obligatoire.")
        )


def validate_refund_amount(payment, refund_amount: Decimal) -> None:
    if payment.transaction_type != PaymentType.CHARGE:
        raise ValidationError(
            _("Seule une transaction de paiement peut être remboursée.")
        )

    if payment.status not in {
        PaymentStatus.SUCCESS,
        PaymentStatus.PARTIALLY_REFUNDED,
    }:
        raise ValidationError(
            _("Cette transaction ne peut pas être remboursée.")
        )

    if refund_amount <= Decimal("0"):
        raise ValidationError(
            _("Le montant du remboursement doit être supérieur à zéro.")
        )

    remaining_amount = (
        payment.amount.amount
        - payment.refunded_amount.amount
    )

    if refund_amount > remaining_amount:
        raise ValidationError(
            _("Le montant du remboursement dépasse le montant restant remboursable.")
        )