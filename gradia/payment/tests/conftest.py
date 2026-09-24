from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from djmoney.money import Money

from gradia.document.tests.factories import DocumentFactory
from gradia.order.models import Order
from gradia.payment.models import Payment
from gradia.utils.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    PaymentType,
)

if TYPE_CHECKING:
    from gradia.document.models import Document
    from gradia.order.models import Order as OrderType
    from gradia.payment.models import Payment as PaymentType
    from gradia.users.models import User


@pytest.fixture
def paid_document() -> Document:
    return DocumentFactory(price=5000)


@pytest.fixture
def order(student, paid_document) -> OrderType:
    return Order.objects.create(
        student=student,
        order_number=f"ORD-PAY-{student.pk}",
        total_amount=Money(5000, "XAF"),
        status=OrderStatus.PENDING,
    )


@pytest.fixture
def other_order(other_user, paid_document) -> OrderType:
    return Order.objects.create(
        student=other_user,
        order_number=f"ORD-PAY-{other_user.pk}",
        total_amount=Money(4000, "XAF"),
        status=OrderStatus.PENDING,
    )


@pytest.fixture
def payment(order) -> PaymentType:
    return Payment.objects.create(
        order=order,
        transaction_type=PaymentType.CHARGE,
        status=PaymentStatus.PENDING,
        amount=Money(5000, "XAF"),
        method=PaymentMethod.CARD,
        provider=PaymentProvider.STRIPE,
        provider_reference="",
    )


@pytest.fixture
def other_payment(other_order) -> PaymentType:
    return Payment.objects.create(
        order=other_order,
        transaction_type=PaymentType.CHARGE,
        status=PaymentStatus.PENDING,
        amount=Money(4000, "XAF"),
        method=PaymentMethod.CARD,
        provider=PaymentProvider.STRIPE,
        provider_reference="",
    )


def completed_session(session_id: str = "cs_test_1", **overrides) -> SimpleNamespace:
    return SimpleNamespace(
        id=session_id,
        payment_status="paid",
        amount_total=5000,
        currency="xaf",
        payment_intent="pi_test_1",
        **overrides,
    )


@pytest.fixture
def fake_stripe_session() -> SimpleNamespace:
    return completed_session()