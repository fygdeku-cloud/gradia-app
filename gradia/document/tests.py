from http import HTTPStatus
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from djmoney.money import Money

from gradia.contest.models import Contest
from gradia.contest.models import ContestCategory
from gradia.contest.models import ContestSession
from gradia.contest.models import Establishment
from gradia.document.models import Document
from gradia.document.services import DocumentServingService
from gradia.order.models import Order
from gradia.order.models import OrderItem
from gradia.payment.models import Payment
from gradia.users.models import User
from gradia.utils.enums import OrderStatus
from gradia.utils.enums import PaymentMethod
from gradia.utils.enums import PaymentProvider
from gradia.utils.enums import PaymentStatus
from gradia.utils.enums import PaymentType


class PurchasedDocumentAccessTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("student@example.com")
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
            subject_file="subjects/math.pdf",
            correction_file="corrections/math.pdf",
            contest_session=session,
        )
        self.order = Order.objects.create(
            student=self.student,
            order_number="GR-ACCESS-TEST",
            total_amount=Money(3500, "XAF"),
            status=OrderStatus.PENDING,
        )
        OrderItem.objects.create(
            order=self.order,
            document=self.document,
            unit_price=Money(3500, "XAF"),
            unit_discount=Money(0, "XAF"),
            quantity=1,
            line_subtotal=Money(3500, "XAF"),
            line_discount=Money(0, "XAF"),
            line_total=Money(3500, "XAF"),
        )
        self.payment = Payment.objects.create(
            order=self.order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.PENDING,
            amount=Money(3500, "XAF"),
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        self.client.force_login(self.student)

    def test_pending_payment_does_not_expose_paid_files_or_download_ctas(self):
        subject_url = reverse(
            "document:download_subject",
            kwargs={"pk": self.document.pk},
        )
        correction_url = reverse(
            "document:view_correction",
            kwargs={"pk": self.document.pk},
        )
        correction_download_url = reverse(
            "document:download_correction",
            kwargs={"pk": self.document.pk},
        )

        assert self.client.get(subject_url).status_code == HTTPStatus.FORBIDDEN
        assert self.client.get(correction_url).status_code == HTTPStatus.FORBIDDEN
        assert (
            self.client.get(correction_download_url).status_code
            == HTTPStatus.FORBIDDEN
        )
        detail = self.client.get(
            reverse("document:detail", kwargs={"pk": self.document.pk}),
        )
        assert detail.status_code == HTTPStatus.OK
        self.assertContains(detail, "Ajouter au panier")
        self.assertNotContains(detail, "Télécharger le sujet")

    def test_confirmed_payment_unlocks_subject_and_inline_correction_only(self):
        self.payment.status = PaymentStatus.SUCCESS
        self.payment.save(update_fields=["status", "updated_at"])
        self.order.status = OrderStatus.SUCCESS
        self.order.save(update_fields=["status", "updated_at"])

        subject_url = reverse(
            "document:download_subject",
            kwargs={"pk": self.document.pk},
        )
        correction_url = reverse(
            "document:view_correction",
            kwargs={"pk": self.document.pk},
        )
        correction_download_url = reverse(
            "document:download_correction",
            kwargs={"pk": self.document.pk},
        )
        with (
            patch.object(
                DocumentServingService,
                "serve_subject_download",
                return_value=HttpResponse("subject"),
            ),
            patch.object(
                DocumentServingService,
                "serve_correction_inline",
                return_value=HttpResponse("correction"),
            ),
        ):
            assert self.client.get(subject_url).status_code == HTTPStatus.OK
            assert self.client.get(correction_url).status_code == HTTPStatus.OK
            assert (
                self.client.get(correction_download_url).status_code
                == HTTPStatus.FORBIDDEN
            )

        detail = self.client.get(
            reverse("document:detail", kwargs={"pk": self.document.pk}),
        )
        self.assertContains(detail, "Télécharger le sujet")
        self.assertContains(detail, "Consulter le corrigé")
        self.assertNotContains(detail, "Télécharger le corrigé")
