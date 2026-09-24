from __future__ import annotations

import json

import pytest
import stripe
from django.test import Client
from django.urls import reverse
from djmoney.money import Money

from gradia.payment.models import PaymentWebhookEvent
from gradia.payment.services.stripe_service import StripePaymentService
from gradia.utils.enums import PaymentStatus, ProcessingStatus


def _json_payload(data: dict) -> bytes:
    return json.dumps(data).encode("utf-8")


class TestPost:
    def test_webhook_url_exists(self):
        assert reverse("payment:webhook") == "/payment/webhook/"

    def test_missing_signature_returns_400_not_403(self):
        # Régression : la vue doit être exempte de CSRF (Stripe n'envoie pas
        # de cookie CSRF) tout en requérant la signature Stripe.
        response = Client(enforce_csrf_checks=True).post(
            reverse("payment:webhook"),
            data=_json_payload({"type": "charge.refunded"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_invalid_signature_returns_400(self):
        def boom(payload, signature, secret):
            raise stripe.error.SignatureVerificationError(signature, "bad")

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(stripe.Webhook, "construct_event", staticmethod(boom))

        response = Client().post(
            reverse("payment:webhook"),
            data=_json_payload({"type": "charge.refunded"}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=abc",
        )
        monkeypatch.undo()
        assert response.status_code == 400

    def test_invalid_payload_returns_400(self):
        response = Client().post(
            reverse("payment:webhook"),
            data=b"not-json{{{{",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=abc",
        )
        assert response.status_code == 400

    def test_valid_event_is_recorded_and_processed(self, db):
        captured = {}

        def fake_construct(raw_payload, signature, secret):
            captured["signature"] = signature
            return {
                "id": "evt_1",
                "type": "charge.refunded",
                "data": {"object": {}},
            }

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(stripe.Webhook, "construct_event", staticmethod(fake_construct))

        payload = _json_payload({"id": "evt_1", "type": "charge.refunded", "data": {}})
        response = Client().post(
            reverse("payment:webhook"),
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=xyz",
        )
        monkeypatch.undo()

        assert response.status_code == 200
        webhook_event = PaymentWebhookEvent.objects.get(event_id="evt_1")
        assert webhook_event.processing_status == ProcessingStatus.PROCESSED
        assert webhook_event.signature == "t=1,v1=xyz"
        assert webhook_event.payload["id"] == "evt_1"
        assert webhook_event.remote_address is not None

    def test_checkout_completed_webhook_confirms_payment(
        self, payment, monkeypatch, fake_stripe_session, client
    ):
        payment.provider_reference = "cs_test_1"
        payment.save(update_fields=["provider_reference", "updated_at"])

        event = {
            "id": "evt_cc",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "metadata": {"payment_id": str(payment.pk)},
                }
            },
        }

        monkeypatch.setattr(
            stripe.Webhook,
            "construct_event",
            staticmethod(lambda raw, signature, secret: event),
        )
        monkeypatch.setattr(
            StripePaymentService,
            "retrieve_checkout_session",
            staticmethod(lambda session_id, **_: fake_stripe_session),
        )

        response = client.post(
            reverse("payment:webhook"),
            data=_json_payload(event),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=real",
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCESS
        assert payment.provider_transaction_id == "pi_test_1"
        assert (
            PaymentWebhookEvent.objects.get(event_id="evt_cc").processing_status
            == ProcessingStatus.PROCESSED
        )