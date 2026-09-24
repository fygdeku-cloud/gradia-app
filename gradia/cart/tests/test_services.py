from __future__ import annotations

import pytest

from gradia.cart.models import Cart
from gradia.cart.services import (
    add_document_to_cart,
    clear_cart,
    get_or_create_cart,
    remove_cart_item,
)


@pytest.mark.django_db
class TestGetOrCreateCart:
    def test_creates_active_cart_for_student(self, student):
        cart = get_or_create_cart(student)

        assert isinstance(cart, Cart)
        assert cart.student == student

    def test_returns_same_cart_on_second_call(self, student):
        first = get_or_create_cart(student)
        second = get_or_create_cart(student)

        assert first.pk == second.pk


@pytest.mark.django_db
class TestAddDocumentToCart:
    def test_adds_published_document_with_price(self, student, paid_document):
        item = add_document_to_cart(student, paid_document.pk)

        assert item.document == paid_document
        assert item.unit_price.amount == paid_document.price

    def test_adding_twice_raises(self, student, paid_document):
        add_document_to_cart(student, paid_document.pk)

        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            add_document_to_cart(student, paid_document.pk)

    def test_unpublished_document_rejected(self, student, unpublished_document):
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            add_document_to_cart(student, unpublished_document.pk)

    def test_missing_document_rejected(self, student):
        import uuid

        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            add_document_to_cart(student, uuid.uuid4())


@pytest.mark.django_db
class TestRemoveCartItem:
    def test_removes_own_item(self, student, paid_document):
        item = add_document_to_cart(student, paid_document.pk)

        remove_cart_item(student, item.pk)

        assert not student.cart.items.exists()

    def test_cannot_remove_other_student_item(self, student, other_user, paid_document):
        from django.core.exceptions import ValidationError

        item = add_document_to_cart(student, paid_document.pk)

        with pytest.raises(ValidationError):
            remove_cart_item(other_user, item.pk)

    def test_missing_item_raises(self, student):
        import uuid

        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            remove_cart_item(student, uuid.uuid4())


@pytest.mark.django_db
class TestClearCart:
    def test_clears_all_items(self, student, paid_document):
        add_document_to_cart(student, paid_document.pk)

        clear_cart(student)

        assert student.cart.items.count() == 0