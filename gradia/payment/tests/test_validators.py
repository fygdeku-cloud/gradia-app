from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from djmoney.money import Money

from gradia.payment.models import Payment
from gradia.payment.validators import (
    validate_order_for_payment,
    validate_payment_amount,
    validate_payment_method_and_provider,
    validate_provider_transaction_id,
    validate_refund_amount,
    validate_user_can_pay,
)
from gradia.utils.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    PaymentType,
)


class TestValidateUserCanPay:
    def test_none_user_rejected(self):
        with pytest.raises(ValidationError):
            validate_user_can_pay(None)

    def test_anonymous_rejected(self, rf):
        request = rf.get("/")
        request.user = type("Anon", (), {"is_authenticated": False})()
        with pytest.raises(ValidationError):
            validate_user_can_pay(request.user)

    def test_non_student_rejected(self, support_staff):
        with pytest.raises(ValidationError):
            validate_user_can_pay(support_staff)

    def test_student_accepted(self, student):
        validate_user_can_pay(student)


class TestValidateOrderForPayment:
    def test_none_order_rejected(self, student):
        with pytest.raises(ValidationError):
            validate_order_for_payment(None, student)

    def test_foreign_order_rejected(self, order, other_user):
        with pytest.raises(ValidationError):
            validate_order_for_payment(order, other_user)

    def test_non_pending_order_rejected(self, order):
        order.status = OrderStatus.SUCCESS
        order.save(update_fields=["status", "updated_at"])
        with pytest.raises(ValidationError):
            validate_order_for_payment(order, order.student)

    def test_zero_amount_rejected(self, order):
        order.total_amount = Money(0, "XAF")
        order.save(update_fields=["total_amount_currency", "total_amount", "updated_at"])
        with pytest.raises(ValidationError):
            validate_order_for_payment(order, order.student)

    def test_valid_order_accepted(self, order):
        validate_order_for_payment(order, order.student)


class TestValidatePaymentMethodAndProvider:
    def test_card_requires_stripe(self):
        with pytest.raises(ValidationError):
            validate_payment_method_and_provider(
                PaymentMethod.CARD,
                PaymentProvider.FLUTTERWAVE_MOBILE_MONEY,
            )

    def test_mobile_money_requires_flutterwave(self):
        with pytest.raises(ValidationError):
            validate_payment_method_and_provider(
                PaymentMethod.MOBILE_MONEY,
                PaymentProvider.STRIPE,
            )

    def test_card_stripe_accepted(self):
        validate_payment_method_and_provider(
            PaymentMethod.CARD, PaymentProvider.STRIPE
        )

    def test_mobile_money_flutterwave_accepted(self):
        validate_payment_method_and_provider(
            PaymentMethod.MOBILE_MONEY,
            PaymentProvider.FLUTTERWAVE_MOBILE_MONEY,
        )


class TestValidatePaymentAmount:
    def test_none_amount_rejected(self, order):
        with pytest.raises(ValidationError):
            validate_payment_amount(None, order)

    def test_mismatch_rejected(self, order):
        with pytest.raises(ValidationError):
            validate_payment_amount(Money(9999, "XAF"), order)

    def test_matching_amount_accepted(self, order):
        validate_payment_amount(Money(5000, "XAF"), order)


class TestValidateProviderTransactionId:
    def test_empty_rejected(self):
        with pytest.raises(ValidationError):
            validate_provider_transaction_id("")

    def test_valid_accepted(self):
        validate_provider_transaction_id("pi_123")


class TestValidateRefundAmount:
    def test_non_charge_rejected(self, order, payment):
        payment = Payment.objects.create(
            order=order,
            transaction_type=PaymentType.REFUND,
            status=PaymentStatus.SUCCESS,
            amount=Money(1000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        with pytest.raises(ValidationError):
            validate_refund_amount(payment, Decimal("500"))

    def test_non_successful_charge_rejected(self, payment):
        with pytest.raises(ValidationError):
            validate_refund_amount(payment, Decimal("500"))

    def test_zero_refund_rejected(self, order):
        payment = Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.SUCCESS,
            amount=Money(5000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        with pytest.raises(ValidationError):
            validate_refund_amount(payment, Decimal("0"))

    def test_refund_exceeding_remaining_rejected(self, order):
        payment = Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.SUCCESS,
            amount=Money(5000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        with pytest.raises(ValidationError):
            validate_refund_amount(payment, Decimal("6000"))

    def test_valid_full_refund_accepted(self, order):
        payment = Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.SUCCESS,
            amount=Money(5000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        validate_refund_amount(payment, Decimal("5000"))

    def test_valid_partial_refund_accepted(self, order):
        payment = Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.PARTIALLY_REFUNDED,
            amount=Money(5000, "XAF"),
            refunded_amount=Money(2000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        validate_refund_amount(payment, Decimal("1000"))