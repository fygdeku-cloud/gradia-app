import pytest
from django.db import IntegrityError
from djmoney.money import Money
from gradia.cart.models import Cart, CartItem
from gradia.document.tests.factories import DocumentFactory
from gradia.users.tests.factories import UserFactory
from gradia.utils.enums import CartStatus


@pytest.mark.django_db
class TestCartModels:
    def test_cart_creation_and_str(self, student):
        cart = Cart.objects.create(student=student, status=CartStatus.ACTIVE)
        assert str(cart) == f"Panier de {student} (Actif)"
        assert cart.items_count == 0

    def test_cart_items_count(self, student):
        cart = Cart.objects.create(student=student, status=CartStatus.ACTIVE)
        doc = DocumentFactory(price=2000)
        CartItem.objects.create(cart=cart, document=doc)
        assert cart.items_count == 1

    def test_cart_item_unique_per_cart(self, student):
        cart = Cart.objects.create(student=student, status=CartStatus.ACTIVE)
        doc = DocumentFactory(price=2000)
        CartItem.objects.create(cart=cart, document=doc)
        with pytest.raises(IntegrityError):
            CartItem.objects.create(cart=cart, document=doc)

    def test_cart_item_unit_price_frozen_from_document(self, student):
        cart = Cart.objects.create(student=student)
        doc = DocumentFactory(price=3500)
        item = CartItem.objects.create(cart=cart, document=doc)
        assert item.unit_price.amount == 3500
        assert item.subtotal.amount == 3500
        assert str(item) == f"{doc} - {cart}"
