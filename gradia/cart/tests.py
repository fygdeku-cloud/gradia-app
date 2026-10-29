from decimal import Decimal
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from gradia.cart.models import Cart
from gradia.cart.models import CartItem
from gradia.contest.models import Contest
from gradia.contest.models import ContestCategory
from gradia.contest.models import ContestSession
from gradia.contest.models import Establishment
from gradia.document.models import Document
from gradia.order.models import Order
from gradia.payment.models import Payment
from gradia.users.models import User
from gradia.utils.enums import CartStatus
from gradia.utils.enums import OrderStatus
from gradia.utils.enums import PaymentMethod
from gradia.utils.enums import PaymentProvider
from gradia.utils.enums import PaymentStatus
from gradia.utils.enums import PaymentType


class CartCheckoutJourneyTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("student@example.com")
        self.other_student = User.objects.create_user("other@example.com")
        establishment = Establishment.objects.create(
            title="Institut",
            name="Institut",
            slug="institut",
        )
        category = ContestCategory.objects.create(title="Concours", slug="concours")
        contest = Contest.objects.create(
            title="Concours A",
            slug="concours-a",
            establishment=establishment,
            category=category,
        )
        session = ContestSession.objects.create(
            title="2026",
            year=2026,
            contest=contest,
        )
        self.document = Document.objects.create(
            title="Sujet de mathématiques",
            price=3500,
            contest_session=session,
        )
        self.client.force_login(self.student)

    def test_add_and_view_cart_uses_backend_price(self):
        response = self.client.post(
            reverse("cart:add", kwargs={"pk": self.document.pk}),
        )

        self.assertRedirects(response, reverse("cart:detail"))
        response = self.client.get(reverse("cart:detail"))
        assert response.status_code == HTTPStatus.OK
        self.assertContains(response, "Sujet de mathématiques")
        self.assertContains(response, "3500")
        assert response.context["cart_total"].amount == Decimal("3500")
        assert CartItem.objects.filter(cart__student=self.student).count() == 1

    def test_checkout_creates_order_and_copies_cart_items_atomically(self):
        self.client.post(reverse("cart:add", kwargs={"pk": self.document.pk}))

        response = self.client.post(reverse("order:checkout"))

        order = Order.objects.get(student=self.student)
        self.assertRedirects(response, reverse("order:detail", kwargs={"pk": order.pk}))
        assert order.total_amount.amount == Decimal("3500")
        assert order.status == OrderStatus.PENDING
        assert order.items.count() == 1
        assert order.items.get().document == self.document
        cart = Cart.objects.get(student=self.student)
        assert cart.status == CartStatus.CONVERTED
        assert not cart.items.exists()

        detail = self.client.get(reverse("order:detail", kwargs={"pk": order.pk}))
        assert detail.status_code == HTTPStatus.OK
        self.assertContains(detail, order.order_number)
        self.assertContains(detail, "3500")

    def test_student_cannot_view_another_students_order(self):
        self.client.post(reverse("cart:add", kwargs={"pk": self.document.pk}))
        self.client.post(reverse("order:checkout"))
        order = Order.objects.get(student=self.student)
        self.client.force_login(self.other_student)

        response = self.client.get(reverse("order:detail", kwargs={"pk": order.pk}))

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_paid_order_shows_only_document_actions_allowed_by_access_service(self):
        self.client.post(reverse("cart:add", kwargs={"pk": self.document.pk}))
        self.client.post(reverse("order:checkout"))
        order = Order.objects.get(student=self.student)
        order.status = OrderStatus.SUCCESS
        order.save(update_fields=["status", "updated_at"])
        Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.SUCCESS,
            amount=order.total_amount,
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        self.document.subject_file = "subjects/math.pdf"
        self.document.correction_file = "corrections/math.pdf"
        self.document.save(
            update_fields=["subject_file", "correction_file", "updated_at"],
        )

        response = self.client.get(reverse("order:detail", kwargs={"pk": order.pk}))

        assert response.status_code == HTTPStatus.OK
        self.assertContains(response, "Télécharger le sujet")
        self.assertContains(response, "Consulter le corrigé")
        self.assertNotContains(response, "Télécharger le corrigé")
