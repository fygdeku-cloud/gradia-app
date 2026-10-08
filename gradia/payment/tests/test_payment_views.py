from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from djmoney.money import Money

from gradia.payment.models import Payment
from gradia.payment.services.stripe_service import StripePaymentService
from gradia.utils.enums import PaymentStatus


def _paid_session(**overrides):
    from types import SimpleNamespace

    defaults = dict(
        id="cs_test_1",
        payment_status="paid",
        amount_total=5000,
        currency="xaf",
        payment_intent="pi_test_1",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestPaymentInitiationView:
    def test_anonymous_redirected_to_login(self, order):
        response = Client().get(
            reverse("payment:initiate", kwargs={"order_id": order.pk})
        )
        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_student_initiation_page(self, client, student, order):
        client.force_login(student)
        response = client.get(
            reverse("payment:initiate", kwargs={"order_id": order.pk})
        )
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["order"] == order
        assert response.context["order"].total_amount == order.total_amount
        assert b"R\xc3\xa9sum\xc3\xa9 de la commande" in response.content
        assert b"Paiement de votre commande" in response.content
        assert b"M\xc3\xa9thode de paiement" in response.content

    def test_missing_order_404(self, client, student):
        client.force_login(student)
        response = client.get(
            reverse("payment:initiate", kwargs={"order_id": "00000000-0000-0000-0000-000000000000"})
        )
        assert response.status_code == 404

    def test_foreign_order_not_reachable(self, client, student, other_order):
        client.force_login(student)
        response = client.get(
            reverse("payment:initiate", kwargs={"order_id": other_order.pk})
        )
        assert response.status_code == 404

    def test_post_creates_payment_and_redirects_to_stripe(
        self, client, student, order, monkeypatch
    ):
        def fake_create(payment, **_):
            return "cs_test_2", "https://checkout.stripe.com/c/pay/cs_test_2"

        monkeypatch.setattr(
            StripePaymentService,
            "create_checkout_session",
            staticmethod(fake_create),
        )

        client.force_login(student)
        response = client.post(
            reverse("payment:initiate", kwargs={"order_id": order.pk}),
            {"method": "card", "provider": "stripe"},
        )

        assert response.status_code == 302
        assert response["Location"] == "https://checkout.stripe.com/c/pay/cs_test_2"

        payment = Payment.objects.get(order=order, transaction_type="charge")
        assert payment.status == PaymentStatus.PENDING
        assert payment.provider_reference == "cs_test_2"
        assert payment.amount == Money(5000, "XAF")
        assert payment.metadata["checkout_session_id"] == "cs_test_2"

    def test_post_invalid_method_provider_400(self, client, student, order):
        client.force_login(student)
        response = client.post(
            reverse("payment:initiate", kwargs={"order_id": order.pk}),
            {"method": "card", "provider": "flutterwave_mobile_money"},
        )
        assert response.status_code == 400
        assert Payment.objects.filter(order=order).count() == 0

    def test_post_missing_order_404(self, client, student):
        client.force_login(student)
        response = client.post(
            reverse("payment:initiate", kwargs={"order_id": "00000000-0000-0000-0000-000000000000"}),
            {"method": "card", "provider": "stripe"},
        )
        assert response.status_code == 404


class TestPaymentProcessingView:
    def test_missing_payment_404(self, client, student):
        client.force_login(student)
        response = client.get(
            reverse("payment:processing", kwargs={"payment_id": "00000000-0000-0000-0000-000000000000"})
        )
        assert response.status_code == 404

    def test_foreign_payment_403(self, client, student, other_payment):
        client.force_login(student)
        response = client.get(
            reverse("payment:processing", kwargs={"payment_id": other_payment.pk})
        )
        assert response.status_code == 403

    def test_already_success_redirects_to_success(self, client, student, payment):
        from gradia.payment.services.transaction_service import TransactionService

        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_test_1",
            provider_response={},
        )
        client.force_login(student)
        response = client.get(
            reverse("payment:processing", kwargs={"payment_id": payment.pk})
        )
        assert response.status_code == 302
        assert reverse("payment:success", kwargs={"payment_id": payment.pk}) in response["Location"]

    def test_pending_without_session_404(self, client, student, payment):
        client.force_login(student)
        response = client.get(
            reverse("payment:processing", kwargs={"payment_id": payment.pk})
        )
        assert response.status_code == 404

    def test_stripe_paid_confirms_and_redirects(
        self, client, student, payment, monkeypatch
    ):
        payment.provider_reference = "cs_test_1"
        payment.save(update_fields=["provider_reference", "updated_at"])
        monkeypatch.setattr(
            StripePaymentService,
            "retrieve_checkout_session",
            staticmethod(lambda session_id, **_: _paid_session()),
        )
        client.force_login(student)
        response = client.get(
            reverse("payment:processing", kwargs={"payment_id": payment.pk})
        )
        payment.refresh_from_db()
        assert response.status_code == 302
        assert reverse("payment:success", kwargs={"payment_id": payment.pk}) in response["Location"]
        assert payment.status == PaymentStatus.SUCCESS
        assert payment.provider_transaction_id == "pi_test_1"

    def test_stripe_not_paid_renders_processing(
        self, client, student, payment, monkeypatch
    ):
        payment.provider_reference = "cs_test_1"
        payment.save(update_fields=["provider_reference", "updated_at"])
        monkeypatch.setattr(
            StripePaymentService,
            "retrieve_checkout_session",
            staticmethod(lambda session_id, **_: _paid_session(payment_status="open")),
        )
        client.force_login(student)
        response = client.get(
            reverse("payment:processing", kwargs={"payment_id": payment.pk})
        )
        assert response.status_code == 200
        assert b"data-payment-status-url" in response.content
        assert b"window.setTimeout(pollStatus" in response.content
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.PENDING


class TestPaymentStatusView:
    def test_returns_status_json(self, client, student, payment):
        client.force_login(student)
        response = client.get(
            reverse("payment:status", kwargs={"payment_id": payment.pk})
        )
        assert response.status_code == 200
        assert response.json()["status"] == PaymentStatus.PENDING
        assert response.json()["payment_id"] == str(payment.pk)

    def test_missing_payment_404(self, client, student):
        client.force_login(student)
        response = client.get(
            reverse("payment:status", kwargs={"payment_id": "00000000-0000-0000-0000-000000000000"})
        )
        assert response.status_code == 404

    def test_foreign_payment_403(self, client, student, other_payment):
        client.force_login(student)
        response = client.get(
            reverse("payment:status", kwargs={"payment_id": other_payment.pk})
        )
        assert response.status_code == 403


class TestPaymentSuccessView:
    def test_success_renders(self, client, student, payment):
        from gradia.payment.services.transaction_service import TransactionService

        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_test_1",
            provider_response={},
        )
        client.force_login(student)
        response = client.get(
            reverse("payment:success", kwargs={"payment_id": payment.pk})
        )
        assert response.status_code == 200

    def test_pending_redirects_to_processing(self, client, student, payment):
        client.force_login(student)
        response = client.get(
            reverse("payment:success", kwargs={"payment_id": payment.pk})
        )
        assert response.status_code == 302
        assert reverse("payment:processing", kwargs={"payment_id": payment.pk}) in response["Location"]

    def test_missing_payment_404(self, client, student):
        client.force_login(student)
        response = client.get(
            reverse("payment:success", kwargs={"payment_id": "00000000-0000-0000-0000-000000000000"})
        )
        assert response.status_code == 404

    def test_foreign_payment_403(self, client, student, other_payment):
        client.force_login(student)
        response = client.get(
            reverse("payment:success", kwargs={"payment_id": other_payment.pk})
        )
        assert response.status_code == 403


class TestPaymentCancelView:
    def test_pending_renders_cancel(self, client, student, payment):
        client.force_login(student)
        response = client.get(
            reverse("payment:cancel", kwargs={"payment_id": payment.pk})
        )
        assert response.status_code == 200

    def test_success_redirects_to_success(self, client, student, payment):
        from gradia.payment.services.transaction_service import TransactionService

        TransactionService.mark_success(
            payment=payment,
            provider_transaction_id="pi_test_1",
            provider_response={},
        )
        client.force_login(student)
        response = client.get(
            reverse("payment:cancel", kwargs={"payment_id": payment.pk})
        )
        assert response.status_code == 302
        assert reverse("payment:success", kwargs={"payment_id": payment.pk}) in response["Location"]


class TestPaymentHistoryView:
    def test_student_renders_history(self, client, student, payment):
        client.force_login(student)
        response = client.get(reverse("payment:history"))
        assert response.status_code == 200
        assert payment in response.context["payments"]

    def test_non_student_403(self, client, support_staff):
        client.force_login(support_staff)
        response = client.get(reverse("payment:history"))
        assert response.status_code == 403

    def test_anonymous_redirected_to_login(self):
        response = Client().get(reverse("payment:history"))
        assert response.status_code == 302
        assert "/users/login/" in response["Location"]