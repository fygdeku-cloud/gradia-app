from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from djmoney.money import Money

from gradia.document.tests.factories import DocumentFactory
from gradia.order.models import Order
from gradia.utils.enums import OrderStatus

if TYPE_CHECKING:
    from gradia.document.models import Document
    from gradia.order.models import Order as OrderType
    from gradia.users.models import User


@pytest.fixture
def paid_document() -> Document:
    return DocumentFactory(price=5000)


@pytest.fixture
def order(student, paid_document) -> OrderType:
    return Order.objects.create(
        student=student,
        order_number=f"ORD-TEST-{student.pk}",
        total_amount=Money(5000, "XAF"),
        status=OrderStatus.PENDING,
    )


@pytest.fixture
def other_order(other_user, paid_document) -> OrderType:
    return Order.objects.create(
        student=other_user,
        order_number=f"ORD-TEST-{other_user.pk}",
        total_amount=Money(4000, "XAF"),
        status=OrderStatus.PENDING,
    )