from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from djmoney.money import Money

from gradia.payment.models import Payment
from gradia.payment.services.transaction_service import TransactionService
from gradia.utils.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    PaymentType,
)


class TestCreateCharge:
    def test_creates_pending_charge(self, order):
        payment = TransactionService.create_charge(
            order=order,
            amount=Money(5000, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )

        payment.refresh_from_db()
        assert payment.transaction_type == PaymentType.CHARGE
        assert payment.status == PaymentStatus.PENDING
        assert payment.amount == Money(5000, "XAF")
        assert payment.method == PaymentMethod.CARD
        assert payment.provider == PaymentProvider.STRIPE
        assert payment.order == order


class TestMarkSuccess:
    def test_marks_success_and_updates_order(self, payment):
        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_123",
            provider_response={"session_id": "cs_test_1"},
        )

        payment.refresh_from_db()
        payment.order.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCESS
        assert payment.provider_transaction_id == "pi_123"
        assert payment.provider_response["session_id"] == "cs_test_1"
        assert payment.processed_at is not None
        assert payment.order.status == OrderStatus.SUCCESS

    def test_already_success_is_idempotent(self, payment):
        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_1",
            provider_response={},
        )
        payment.refresh_from_db()
        result = TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_2",
            provider_response={"new": True},
        )

        payment.refresh_from_db()
        assert result.status == PaymentStatus.SUCCESS
        assert payment.provider_transaction_id == "pi_1"

    def test_rejects_non_charge(self, order, payment):
        payment.transaction_type = PaymentType.REFUND
        payment.save(update_fields=["transaction_type", "updated_at"])
        with pytest.raises(ValidationError):
            TransactionService.mark_success(
                payment=payment,
                provider_transaction_id="pi_1",
                provider_response={},
            )

    def test_rejects_non_pending(self, payment):
        payment.status = PaymentStatus.FAILED
        payment.save(update_fields=["status", "updated_at"])
        with pytest.raises(ValidationError):
            TransactionService.mark_success(
                payment=payment,
                provider_transaction_id="pi_1",
                provider_response={},
            )

    def test_rejects_missing_provider_transaction_id(self, payment):
        with pytest.raises(ValidationError):
            TransactionService.mark_success(
                payment=payment,
                provider_transaction_id="",
                provider_response={},
            )


class TestMarkFailed:
    def test_marks_pending_as_failed(self, payment):
        TransactionService.mark_failed(
            payment=payment,
            provider_response={"error": "card_declined"},
            failure_reason="Décliné",
        )

        payment.refresh_from_db()
        assert payment.status == PaymentStatus.FAILED
        assert payment.failure_reason == "Décliné"
        assert payment.provider_response["error"] == "card_declined"
        assert payment.processed_at is not None

    def test_success_never_becomes_failed(self, payment):
        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_1",
            provider_response={},
        )
        payment.refresh_from_db()
        result = TransactionService.mark_failed(
            payment=payment,
            provider_response={},
            failure_reason="impossible",
        )
        payment.refresh_from_db()
        assert result.status == PaymentStatus.SUCCESS
        assert payment.status == PaymentStatus.SUCCESS
        assert payment.failure_reason == ""

    def test_already_failed_unchanged(self, payment):
        TransactionService.mark_failed(
            payment=payment, provider_response={}, failure_reason="1"
        )
        payment.refresh_from_db()
        result = TransactionService.mark_failed(
            payment=payment, provider_response={}, failure_reason="2"
        )
        payment.refresh_from_db()
        assert result.status == PaymentStatus.FAILED
        assert payment.failure_reason == "1"


class TestMarkCancelled:
    def test_marks_pending_as_cancelled(self, payment):
        TransactionService.mark_cancelled(
            payment=payment,
            provider_response={"status": "expired"},
            failure_reason="Session expirée",
        )

        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CANCELLED
        assert payment.failure_reason == "Session expirée"
        assert payment.processed_at is not None

    def test_success_not_cancelled(self, payment):
        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_1",
            provider_response={},
        )
        payment.refresh_from_db()
        result = TransactionService.mark_cancelled(
            payment=payment, provider_response={}, failure_reason="x"
        )
        payment.refresh_from_db()
        assert result.status == PaymentStatus.SUCCESS
        assert payment.status == PaymentStatus.SUCCESS

    def test_already_cancelled_unchanged(self, payment):
        TransactionService.mark_cancelled(
            payment=payment, provider_response={}, failure_reason="1"
        )
        payment.refresh_from_db()
        result = TransactionService.mark_cancelled(
            payment=payment, provider_response={}, failure_reason="2"
        )
        payment.refresh_from_db()
        assert result.status == PaymentStatus.CANCELLED
        assert payment.failure_reason == "1"


class TestMarkFraud:
    def test_marks_pending_as_fraud(self, payment):
        TransactionService.mark_fraud(
            payment=payment,
            provider_response={"amount_total": 9999},
            failure_reason="Montant incohérent",
        )

        payment.refresh_from_db()
        assert payment.status == PaymentStatus.FRAUD
        assert payment.failure_reason == "Montant incohérent"
        assert payment.provider_response["amount_total"] == 9999
        assert payment.processed_at is not None

    def test_success_not_marked_fraud(self, payment):
        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_1",
            provider_response={},
        )
        payment.refresh_from_db()
        result = TransactionService.mark_fraud(
            payment=payment,
            provider_response={},
            failure_reason="x",
        )
        payment.refresh_from_db()
        assert result.status == PaymentStatus.SUCCESS
        assert payment.status == PaymentStatus.SUCCESS