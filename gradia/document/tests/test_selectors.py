from __future__ import annotations

from djmoney.money import Money
from django.contrib.auth.models import AnonymousUser

import pytest

from gradia.document.selectors import (
    annotate_with_paid_status,
    get_paid_document_ids_for_user,
    get_published_documents,
)
from gradia.order.models import Order, OrderItem
from gradia.payment.models import Payment
from gradia.payment.services.transaction_service import TransactionService
from gradia.utils.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentType,
)


def _build_paid_order(user, document) -> Order:
    """Commande + charge réussie contenant le document (paiement confirmé)."""
    order = Order.objects.create(
        student=user,
        order_number=f"ORD-PAID-{document.pk.hex[:10].upper()}",
        total_amount=Money(document.price, "XAF"),
        status=OrderStatus.PENDING,
    )
    OrderItem.objects.create(
        order=order,
        document=document,
        unit_price=Money(document.price, "XAF"),
        quantity=1,
        line_subtotal=Money(document.price, "XAF"),
        line_total=Money(document.price, "XAF"),
    )
    TransactionService.create_charge(
        order=order,
        amount=Money(document.price, "XAF"),
        method=PaymentMethod.CARD,
        provider=PaymentProvider.STRIPE,
    )
    payment = Payment.objects.get(order=order, transaction_type=PaymentType.CHARGE)
    TransactionService.mark_success(
        payment=payment,
        provider_transaction_id="pi_test_paid",
        provider_response={"ok": True},
    )
    return order


@pytest.mark.django_db
class TestPaidStatusAnnotations:
    def test_anonymous_user_never_paid(self, document):
        queryset = annotate_with_paid_status(get_published_documents(), None)

        assert queryset.get(pk=document.pk).has_paid is False

    def test_unauthenticated_user_never_paid(self, document):
        queryset = annotate_with_paid_status(get_published_documents(), AnonymousUser())

        assert queryset.get(pk=document.pk).has_paid is False

    def test_user_without_payment_has_not_paid(self, student, document):
        queryset = annotate_with_paid_status(get_published_documents(), student)

        assert queryset.get(pk=document.pk).has_paid is False

    def test_user_with_confirmed_payment_has_paid(self, student, document):
        _build_paid_order(student, document)

        queryset = annotate_with_paid_status(get_published_documents(), student)

        assert queryset.get(pk=document.pk).has_paid is True

    def test_paid_document_ids_for_user(self, student, document):
        _build_paid_order(student, document)

        paid_ids = list(get_paid_document_ids_for_user(student))

        assert paid_ids == [document.pk]

    def test_paid_document_ids_empty_for_anonymous(self, document):
        assert list(get_paid_document_ids_for_user(None)) == []