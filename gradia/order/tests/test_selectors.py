from __future__ import annotations

import uuid

import pytest

from gradia.order.selectors import get_order_detail, get_user_orders


@pytest.mark.django_db
class TestOrderSelectors:
    def test_get_user_orders_only_own(self, order, other_order, student):
        assert list(get_user_orders(student)) == [order]

    def test_get_order_detail_returns_own(self, order, student):
        assert get_order_detail(student, order.pk) == order

    def test_get_order_detail_returns_none_for_foreign_order(
        self,
        order,
        other_user,
    ):
        """Régression P4 : la suppression du DoesNotExist évite le 500."""
        assert get_order_detail(other_user, order.pk) is None

    def test_get_order_detail_returns_none_for_missing(self, student):
        assert get_order_detail(student, uuid.uuid4()) is None

    def test_get_order_detail_prefetches_items(self, order, student, paid_document):
        from gradia.order.models import OrderItem

        OrderItem.objects.create(
            order=order,
            document=paid_document,
            unit_price=order.total_amount,
            quantity=1,
            line_subtotal=order.total_amount,
            line_total=order.total_amount,
        )

        detail = get_order_detail(student, order.pk)

        assert detail is not None
        assert list(detail.items.all())