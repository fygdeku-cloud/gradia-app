from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestOrderListView:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse("order:list"))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_plain_student_can_list_own_orders(self, client, student, order):
        client.force_login(student)

        response = client.get(reverse("order:list"))

        assert response.status_code == 200
        assert order in response.context["orders"]

    def test_staff_not_student_is_forbidden(self, client, support_staff, order):
        client.force_login(support_staff)

        response = client.get(reverse("order:list"))

        assert response.status_code == 403


@pytest.mark.django_db
class TestOrderDetailView:
    def test_anonymous_redirected_to_login(self, client, order):
        response = client.get(reverse("order:detail", kwargs={"pk": order.pk}))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_owner_can_view_own_order(self, client, student, order):
        client.force_login(student)

        response = client.get(reverse("order:detail", kwargs={"pk": order.pk}))

        assert response.status_code == 200
        assert response.context["order"] == order

    def test_foreign_student_gets_404(self, client, other_user, order):
        """Régression O1/P4 : URL en UUID + aucun DoesNotExist → 404 propre."""
        client.force_login(other_user)

        response = client.get(reverse("order:detail", kwargs={"pk": order.pk}))

        assert response.status_code == 404

    def test_missing_order_gets_404(self, client, student):
        client.force_login(student)

        response = client.get(
            reverse(
                "order:detail",
                kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
            )
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestCheckoutView:
    def test_anonymous_redirected_to_login(self, client):
        response = client.post(reverse("order:checkout"))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_empty_cart_flashes_error_and_redirects(self, client, student):
        from gradia.cart.models import Cart

        Cart.objects.create(student=student)
        client.force_login(student)

        response = client.post(reverse("order:checkout"))

        assert response.status_code == 302
        assert response["Location"] == reverse("cart:detail")

    def test_checkout_creates_order_and_redirects_to_detail(
        self,
        client,
        student,
        paid_document,
    ):
        from gradia.cart.models import Cart, CartItem
        from gradia.order.models import Order

        cart = Cart.objects.create(student=student)
        CartItem.objects.create(cart=cart, document=paid_document)
        client.force_login(student)

        response = client.post(reverse("order:checkout"))

        assert response.status_code == 302
        order = Order.objects.get(student=student)
        assert response["Location"] == reverse("order:detail", kwargs={"pk": order.pk})