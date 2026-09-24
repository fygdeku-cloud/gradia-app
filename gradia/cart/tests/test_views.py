from __future__ import annotations

import pytest
from django.urls import reverse

from gradia.cart.services import add_document_to_cart


@pytest.mark.django_db
class TestCartDetailView:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse("cart:detail"))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_empty_cart_renders(self, client, student):
        client.force_login(student)

        response = client.get(reverse("cart:detail"))

        assert response.status_code == 200
        assert list(response.context["items"]) == []

    def test_cart_with_items_renders(self, client, student, paid_document):
        add_document_to_cart(student, paid_document.pk)
        client.force_login(student)

        response = client.get(reverse("cart:detail"))

        assert response.status_code == 200
        assert len(response.context["items"]) == 1


@pytest.mark.django_db
class TestAddToCartView:
    def test_valid_for_uuid_document_id(self, client, student, paid_document):
        """Régression O3 : document_id est un UUID, pas un entier."""
        client.force_login(student)

        response = client.post(
            reverse("cart:add"),
            data={"document_id": str(paid_document.pk)},
        )

        assert response.status_code == 302
        assert student.cart.items.count() == 1

    def test_invalid_document_id_redirects_without_mutation(
        self,
        client,
        student,
    ):
        from gradia.cart.models import CartItem

        client.force_login(student)

        response = client.post(
            reverse("cart:add"),
            data={"document_id": "not-a-uuid"},
        )

        assert response.status_code == 302
        assert CartItem.objects.filter(cart__student=student).count() == 0


@pytest.mark.django_db
class TestRemoveCartItemView:
    def test_removes_item_by_uuid(self, client, student, paid_document):
        item = add_document_to_cart(student, paid_document.pk)
        client.force_login(student)

        response = client.post(
            reverse("cart:remove", kwargs={"item_id": item.pk}),
        )

        assert response.status_code == 302
        assert student.cart.items.count() == 0

    def test_cannot_remove_other_student_item(self, client, student, other_user, paid_document):
        item = add_document_to_cart(student, paid_document.pk)
        client.force_login(other_user)

        response = client.post(
            reverse("cart:remove", kwargs={"item_id": item.pk}),
        )

        assert response.status_code == 302
        assert student.cart.items.count() == 1


@pytest.mark.django_db
class TestClearCartView:
    def test_clears_cart(self, client, student, paid_document):
        add_document_to_cart(student, paid_document.pk)
        client.force_login(student)

        response = client.post(reverse("cart:clear"))

        assert response.status_code == 302
        assert student.cart.items.count() == 0