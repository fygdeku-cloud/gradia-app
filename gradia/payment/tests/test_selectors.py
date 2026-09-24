from __future__ import annotations

import uuid

import pytest
from djmoney.money import Money

from gradia.payment.models import Payment
from gradia.payment.selectors import (
    get_order_payments,
    get_order_payments_by_status,
    get_payment,
    get_payment_by_provider_reference,
    get_payment_by_provider_transaction_id,
    get_pending_charge_for_order,
    get_pending_payments,
    get_refunds_for_payment,
    get_successful_charge_for_order,
    get_successful_payments,
    get_user_payments,
)
from gradia.payment.services.transaction_service import TransactionService
from gradia.utils.enums import (
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    PaymentType,
)


class TestGetPayment:
    def test_returns_payment(self, payment):
        assert get_payment(payment.pk) == payment

    def test_nonexistent_returns_none(self, db):
        assert get_payment(uuid.uuid4()) is None


class TestGetUserPayments:
    def test_returns_only_own_orders(self, student, other_user, payment, other_payment):
        results = list(get_user_payments(student))
        assert payment in results
        assert other_payment not in results

    def test_orders_by_most_recent(self, student, order):
        older = Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.PENDING,
            amount=Money(5000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        newer = Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.PENDING,
            amount=Money(5000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        assert list(get_user_payments(student))[0] == newer
        assert older in list(get_user_payments(student))


class TestGetOrderPayments:
    def test_returns_order_payments(self, order, payment, other_payment):
        assert list(get_order_payments(order)) == [payment]

    def test_filter_by_status(self, order, payment):
        assert payment in get_order_payments_by_status(order, PaymentStatus.PENDING)
        assert list(get_order_payments_by_status(order, PaymentStatus.SUCCESS)) == []


class TestGetSuccessfulChargeForOrder:
    def test_returns_success_charge(self, order, payment, other_payment):
        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_1",
            provider_response={},
        )
        assert get_successful_charge_for_order(order) == payment

    def test_pending_returns_none(self, order, payment):
        assert get_successful_charge_for_order(order) is None


class TestGetPendingChargeForOrder:
    def test_returns_pending(self, order, payment):
        assert get_pending_charge_for_order(order) == payment

    def test_success_returns_none(self, order, payment):
        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_1",
            provider_response={},
        )
        assert get_pending_charge_for_order(order) is None


class TestGetPaymentByProviderReference:
    def test_empty_reference_returns_none(self):
        assert get_payment_by_provider_reference("") is None

    def test_matching_reference(self, payment):
        payment.provider_reference = "cs_ref_1"
        payment.save(update_fields=["provider_reference", "updated_at"])
        assert get_payment_by_provider_reference("cs_ref_1") == payment

    def test_unknown_reference_returns_none(self, db):
        assert get_payment_by_provider_reference("cs_unknown") is None


class TestGetPaymentByProviderTransactionId:
    def test_empty_id_returns_none(self):
        assert get_payment_by_provider_transaction_id("") is None

    def test_matching_id(self, payment):
        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_42",
            provider_response={},
        )
        assert get_payment_by_provider_transaction_id("pi_42") == payment

    def test_unknown_id_returns_none(self, db):
        assert get_payment_by_provider_transaction_id("pi_unknown") is None


class TestGetRefundsForPayment:
    def test_returns_refund_children(self, order, payment):
        refund = Payment.objects.create(
            order=order,
            parent=payment,
            transaction_type=PaymentType.REFUND,
            status=PaymentStatus.SUCCESS,
            amount=Money(1000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        partial = Payment.objects.create(
            order=order,
            parent=payment,
            transaction_type=PaymentType.PARTIAL_REFUND,
            status=PaymentStatus.SUCCESS,
            amount=Money(500, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        results = list(get_refunds_for_payment(payment))
        assert refund in results
        assert partial in results

    def test_ignores_charges(self, order, payment):
        child = Payment.objects.create(
            order=order,
            parent=payment,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.PENDING,
            amount=Money(5000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        assert list(get_refunds_for_payment(payment)) == []
        assert child.pk  # sanity


class TestFinancialQueries:
    def test_get_successful_payments_scoped_by_user(
        self, student, payment, other_payment
    ):
        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_1",
            provider_response={},
        )
        TransactionService.mark_success(
            payment=other_payment,
            provider_transaction_id="pi_2",
            provider_response={},
        )
        results = list(get_successful_payments(student))
        assert payment in results
        assert other_payment not in results

    def test_get_pending_payments_scoped_by_user(
        self, student, payment, other_payment
    ):
        results = list(get_pending_payments(student))
        assert payment in results
        assert other_payment not in results