from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from gradia.order.models import Order, OrderItem
from gradia.order.services import create_order_from_cart


@pytest.mark.django_db
class TestCreateOrderFromCart:
    def test_creates_order_with_items_and_clears_cart(self, student, paid_document):
        from gradia.cart.models import Cart, CartItem

        cart = Cart.objects.create(student=student)
        CartItem.objects.create(cart=cart, document=paid_document)

        order = create_order_from_cart(student, cart)

        assert order.student == student
        assert order.items.count() == 1
        assert order.items.first().document == paid_document
        assert cart.items.count() == 0

    def test_rejects_empty_cart(self, student):
        from gradia.cart.models import Cart

        cart = Cart.objects.create(student=student)

        with pytest.raises(ValidationError):
            create_order_from_cart(student, cart)

        assert Order.objects.count() == 0

    def test_rejects_foreign_cart(self, student, other_user):
        from gradia.cart.models import Cart

        cart = Cart.objects.create(student=other_user)

        with pytest.raises(ValidationError):
            create_order_from_cart(student, cart)

        assert Order.objects.count() == 0

    def test_order_items_are_persisted(self, student, paid_document):
        from gradia.cart.models import Cart, CartItem

        cart = Cart.objects.create(student=student)
        CartItem.objects.create(cart=cart, document=paid_document)

        order = create_order_from_cart(student, cart)

        assert OrderItem.objects.filter(order=order).count() == 1
        assert order.order_number.startswith("ORD-")