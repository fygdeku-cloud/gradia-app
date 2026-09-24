from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from gradia.payment.models import PaymentWebhookEvent
from gradia.payment.services.stripe_service import StripePaymentService
from gradia.payment.services.webhook_service import WebhookService
from gradia.utils.enums import (
    PaymentProvider,
    PaymentStatus,
    ProcessingStatus,
)


def checkout_completed_event(payment, session_id="cs_test_1", **extra):
    data = {
        "id": session_id,
        "metadata": {"payment_id": str(payment.pk)},
    }
    return {
        "id": "evt_test_1",
        "type": "checkout.session.completed",
        "data": {"object": {**data, **extra}},
    }


def get_stripe_session(**overrides):
    from types import SimpleNamespace

    defaults = {
        "id": "cs_test_1",
        "payment_status": "paid",
        "amount_total": 5000,
        "currency": "xaf",
        "payment_intent": "pi_test_1",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestCheckoutCompleted:
    def test_marks_payment_success(self, payment, monkeypatch, fake_stripe_session):
        payment.provider_reference = "cs_test_1"
        payment.save(update_fields=["provider_reference", "updated_at"])

        def fake_retrieve(session_id, **_):
            assert session_id == "cs_test_1"
            return fake_stripe_session

        monkeypatch.setattr(
            StripePaymentService, "retrieve_checkout_session", staticmethod(fake_retrieve)
        )

        service = WebhookService()
        webhook_event = service.process_event(
            event=checkout_completed_event(payment),
            payload={"id": "evt_test_1"},
            signature="sig_t",
            remote_address="127.0.0.1",
        )

        payment.refresh_from_db()
        payment.order.refresh_from_db()
        assert webhook_event.processing_status == ProcessingStatus.PROCESSED
        assert webhook_event.processed_at is not None
        assert payment.status == PaymentStatus.SUCCESS
        assert payment.provider_transaction_id == "pi_test_1"
        assert payment.provider_response["session_id"] == "cs_test_1"
        assert payment.order.status == "SUCCESS"

    def test_is_idempotent(self, payment, monkeypatch, fake_stripe_session):
        payment.provider_reference = "cs_test_1"
        payment.save(update_fields=["provider_reference", "updated_at"])

        calls = {"n": 0}

        def fake_retrieve(session_id, **_):
            calls["n"] += 1
            return fake_stripe_session

        monkeypatch.setattr(
            StripePaymentService, "retrieve_checkout_session", staticmethod(fake_retrieve)
        )

        service = WebhookService()
        event = checkout_completed_event(payment)
        service.process_event(
            event=event, payload={}, signature="sig_t", remote_address="127.0.0.1"
        )
        service.process_event(
            event=event, payload={}, signature="sig_t", remote_address="127.0.0.1"
        )

        assert calls["n"] == 1
        assert (
            PaymentWebhookEvent.objects.filter(
                provider=PaymentProvider.STRIPE, event_id="evt_test_1"
            ).count()
            == 1
        )

    def test_missing_payment_id_metadata(self, payment):
        event = {
            "id": "evt_bad",
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_1", "metadata": {}}},
        }
        service = WebhookService()
        with pytest.raises(ValidationError):
            service.process_event(
                event=event, payload={}, signature="", remote_address="127.0.0.1"
            )

        webhook_event = PaymentWebhookEvent.objects.get(event_id="evt_bad")
        assert webhook_event.processing_status == ProcessingStatus.FAILED
        assert "métadonnées" in webhook_event.error_message
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.PENDING

    def test_mismatched_checkout_session(self, payment):
        payment.provider_reference = "cs_other"
        payment.save(update_fields=["provider_reference", "updated_at"])
        service = WebhookService()
        with pytest.raises(ValidationError):
            service.process_event(
                event=checkout_completed_event(payment),
                payload={},
                signature="",
                remote_address="127.0.0.1",
            )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.PENDING

    def test_stripe_not_paid_yet(self, payment, monkeypatch, fake_stripe_session):
        payment.provider_reference = "cs_test_1"
        payment.save(update_fields=["provider_reference", "updated_at"])

        monkeypatch.setattr(
            StripePaymentService,
            "retrieve_checkout_session",
            staticmethod(lambda session_id, **_: get_stripe_session(payment_status="open")),
        )

        service = WebhookService()
        with pytest.raises(ValidationError):
            service.process_event(
                event=checkout_completed_event(payment),
                payload={},
                signature="",
                remote_address="127.0.0.1",
            )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.PENDING

    def test_amount_mismatch_marks_fraud(self, payment, monkeypatch):
        payment.provider_reference = "cs_test_1"
        payment.save(update_fields=["provider_reference", "updated_at"])
        monkeypatch.setattr(
            StripePaymentService,
            "retrieve_checkout_session",
            staticmethod(lambda session_id, **_: get_stripe_session(amount_total=9000)),
        )

        service = WebhookService()
        webhook_event = service.process_event(
            event=checkout_completed_event(payment),
            payload={},
            signature="",
            remote_address="127.0.0.1",
        )

        payment.refresh_from_db()
        assert webhook_event.processing_status == ProcessingStatus.PROCESSED
        assert payment.status == PaymentStatus.FRAUD
        assert payment.provider_response["amount_total"] == 9000


class TestCheckoutExpired:
    def test_expired_marks_cancelled(self, payment):
        event = {
            "id": "evt_exp",
            "type": "checkout.session.expired",
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "status": "expired",
                    "metadata": {"payment_id": str(payment.pk)},
                }
            },
        }
        webhook_event = WebhookService().process_event(
            event=event, payload={}, signature="", remote_address="127.0.0.1"
        )
        payment.refresh_from_db()
        assert webhook_event.processing_status == ProcessingStatus.PROCESSED
        assert payment.status == PaymentStatus.CANCELLED


class TestAsyncPaymentFailed:
    def test_async_failure_marks_failed(self, payment):
        event = {
            "id": "evt_af",
            "type": "checkout.session.async_payment_failed",
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "payment_status": "unpaid",
                    "metadata": {"payment_id": str(payment.pk)},
                }
            },
        }
        webhook_event = WebhookService().process_event(
            event=event, payload={}, signature="", remote_address="127.0.0.1"
        )
        payment.refresh_from_db()
        assert webhook_event.processing_status == ProcessingStatus.PROCESSED
        assert payment.status == PaymentStatus.FAILED


class TestUnknownEvent:
    def test_ignored_but_processed(self, payment):
        event = {
            "id": "evt_unknown",
            "type": "charge.refund.updated",
            "data": {"object": {}},
        }
        webhook_event = WebhookService().process_event(
            event=event, payload={}, signature="", remote_address="127.0.0.1"
        )
        assert webhook_event.processing_status == ProcessingStatus.PROCESSED
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.PENDING


class TestFailureDiagnostics:
    def test_dispatch_exception_records_failed_status(self, db, monkeypatch):
        def boom(self, event):
            raise RuntimeError("panic interne")

        monkeypatch.setattr(WebhookService, "_dispatch", boom)

        service = WebhookService()
        event = {"id": "evt_boom", "type": "checkout.session.completed", "data": {"object": {}}}
        with pytest.raises(RuntimeError):
            service.process_event(
                event=event, payload={}, signature="", remote_address="1.2.3.4"
            )

        webhook_event = PaymentWebhookEvent.objects.get(event_id="evt_boom")
        assert webhook_event.processing_status == ProcessingStatus.FAILED
        assert "panic interne" in webhook_event.error_message
        assert webhook_event.processed_at is not None

    def test_failed_event_is_retried(self, db, monkeypatch):
        calls = {"n": 0}

        def flaky(self, event):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("première tentative")

        monkeypatch.setattr(WebhookService, "_dispatch", flaky)

        event = {
            "id": "evt_retry",
            "type": "charge.refund.updated",
            "data": {},
        }
        service = WebhookService()
        with pytest.raises(RuntimeError):
            service.process_event(event=event, payload={}, signature="", remote_address="")

        webhook_event = service.process_event(
            event=event, payload={}, signature="", remote_address=""
        )
        assert calls["n"] == 2
        assert webhook_event.processing_status == ProcessingStatus.PROCESSED