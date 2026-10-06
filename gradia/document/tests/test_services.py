import io
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import ProtectedError
from django.http import FileResponse
from gradia.document.forms import DocumentCreateForm, DocumentUpdateForm
from gradia.document.models import Document, DocumentAccessLog
from gradia.document.services import (
    DocumentAccessLogService,
    DocumentAccessService,
    DocumentServingService,
    DocumentService,
)
from gradia.document.tests.factories import ContestSessionFactory, DocumentFactory
from gradia.order.models import Order, OrderItem
from gradia.payment.models import Payment
from gradia.users.tests.factories import UserFactory
from gradia.utils.enums import (
    ACTION_DOWNLOAD_SUBJECT,
    ACTION_VIEW_CORRECTION,
    OrderStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    PaymentType,
)


@pytest.mark.django_db
class TestDocumentService:
    def test_publish_and_unpublish(self):
        doc = DocumentFactory(is_published=False)
        published = DocumentService.publish(document=doc)
        assert published.is_published is True
        doc.refresh_from_db()
        assert doc.is_published is True

        # Re-publishing is idempotent
        DocumentService.publish(document=doc)
        assert doc.is_published is True

        unpublished = DocumentService.unpublish(document=doc)
        assert unpublished.is_published is False
        doc.refresh_from_db()
        assert doc.is_published is False

        # Re-unpublishing is idempotent
        DocumentService.unpublish(document=doc)
        assert doc.is_published is False

    def test_delete_document(self):
        doc = DocumentFactory()
        doc_id = doc.pk
        DocumentService.delete(document=doc)
        assert not Document.objects.filter(pk=doc_id).exists()

    def test_update_replaces_files(self, student):
        doc = DocumentFactory(title="Ancien titre")
        session = ContestSessionFactory()
        new_subject = SimpleUploadedFile(
            "nouveau-sujet.pdf",
            b"%PDF-1.4\nsubject",
            content_type="application/pdf",
        )
        new_correction = SimpleUploadedFile(
            "nouveau-corrige.pdf",
            b"%PDF-1.4\ncorrection",
            content_type="application/pdf",
        )
        form = DocumentUpdateForm(
            data={
                "title": "Nouveau titre",
                "description": doc.description,
                "context": doc.context,
                "contest_session": session.pk,
                "price": doc.price,
                "is_published": "on",
            },
            files={"subject_file": new_subject, "correction_file": new_correction},
        )
        assert form.is_valid(), form.errors

        updated = DocumentService.update(document=doc, form=form)
        updated.refresh_from_db()

        assert updated.title == "Nouveau titre"
        assert updated.subject_file.name.endswith("nouveau-sujet.pdf")
        assert updated.correction_file.name.endswith("nouveau-corrige.pdf")

    def test_update_keeps_files_when_not_reuploaded(self):
        doc = DocumentFactory()
        session = ContestSessionFactory()
        subject_name = doc.subject_file.name
        correction_name = doc.correction_file.name
        form = DocumentUpdateForm(
            data={
                "title": doc.title,
                "description": doc.description,
                "context": doc.context,
                "contest_session": session.pk,
                "price": doc.price,
                "is_published": "on",
            },
        )
        assert form.is_valid(), form.errors

        updated = DocumentService.update(document=doc, form=form)
        updated.refresh_from_db()

        assert updated.subject_file.name == subject_name
        assert updated.correction_file.name == correction_name

    def test_delete_blocked_when_referenced_by_order_keeps_files(self, student):
        doc = DocumentFactory()
        subject_name = doc.subject_file.name
        correction_name = doc.correction_file.name
        storage = doc.subject_file.field.storage
        order = Order.objects.create(
            student=student,
            order_number="ORD-BLOCKED",
            total_amount=doc.price,
            status=OrderStatus.PENDING,
        )
        OrderItem.objects.create(
            order=order,
            document=doc,
            unit_price=doc.price,
            quantity=1,
            line_total=doc.price,
        )

        with pytest.raises(ProtectedError):
            DocumentService.delete(document=doc)

        assert Document.objects.filter(pk=doc.pk).exists()
        assert storage.exists(subject_name)
        assert storage.exists(correction_name)


@pytest.mark.django_db
class TestDocumentAccessService:
    def test_can_view_document(self, student):
        pub_doc = DocumentFactory(is_published=True)
        unpub_doc = DocumentFactory(is_published=False)
        staff = UserFactory(is_staff=True, is_student=False)

        assert DocumentAccessService.can_view_document(student, pub_doc) is True
        assert DocumentAccessService.can_view_document(student, unpub_doc) is False
        assert DocumentAccessService.can_view_document(staff, unpub_doc) is True

    def test_can_download_subject_free_vs_paid(self, student):
        free_doc = DocumentFactory(price=0, is_published=True)
        paid_doc = DocumentFactory(price=3000, is_published=True)
        staff = UserFactory(is_staff=True, is_student=False)

        # Unauthenticated user can download free subject
        assert DocumentAccessService.can_download_subject(None, free_doc) is True
        assert DocumentAccessService.can_download_subject(None, paid_doc) is False

        # Student without payment
        assert DocumentAccessService.can_download_subject(student, free_doc) is True
        assert DocumentAccessService.can_download_subject(student, paid_doc) is False

        # Staff can always download
        assert DocumentAccessService.can_download_subject(staff, paid_doc) is True

    def test_can_download_subject_with_confirmed_payment(self, student):
        paid_doc = DocumentFactory(price=3000, is_published=True)
        order = Order.objects.create(student=student, order_number="ORD-1", total_amount=3000, status=OrderStatus.SUCCESS)
        OrderItem.objects.create(order=order, document=paid_doc, unit_price=3000, quantity=1, line_total=3000)
        Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.SUCCESS,
            amount=3000,
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )

        assert DocumentAccessService.can_download_subject(student, paid_doc) is True

    def test_can_view_correction_rules(self, student):
        free_doc = DocumentFactory(price=0, is_published=True)
        paid_doc = DocumentFactory(price=2000, is_published=True)
        staff = UserFactory(is_staff=True, is_student=False)

        # Unauthenticated cannot view correction (even free requires auth)
        assert DocumentAccessService.can_view_correction(None, free_doc) is False

        # Authenticated student can view free doc correction
        assert DocumentAccessService.can_view_correction(student, free_doc) is True

        # Unpaid student cannot view paid correction
        assert DocumentAccessService.can_view_correction(student, paid_doc) is False

        # Staff can view
        assert DocumentAccessService.can_view_correction(staff, paid_doc) is True

    def test_can_download_correction_strictly_for_staff(self, student):
        paid_doc = DocumentFactory(price=2000, is_published=True)
        order = Order.objects.create(student=student, order_number="ORD-123", total_amount=2000, status=OrderStatus.SUCCESS)
        OrderItem.objects.create(order=order, document=paid_doc, unit_price=2000, quantity=1, line_total=2000)
        Payment.objects.create(
            order=order,
            transaction_type=PaymentType.CHARGE,
            status=PaymentStatus.SUCCESS,
            amount=2000,
            method=PaymentMethod.CARD,
            provider=PaymentProvider.STRIPE,
        )
        staff = UserFactory(is_staff=True, is_student=False)

        # Student paid can view correction, but NEVER download correction
        assert DocumentAccessService.can_view_correction(student, paid_doc) is True
        assert DocumentAccessService.can_download_correction(student, paid_doc) is False

        # Staff can download correction
        assert DocumentAccessService.can_download_correction(staff, paid_doc) is True


@pytest.mark.django_db
class TestDocumentServingAndLogs:
    def test_serve_subject_download(self, student):
        free_doc = DocumentFactory(price=0, is_published=True)
        response = DocumentServingService.serve_subject_download(user=student, document=free_doc)
        assert isinstance(response, FileResponse)
        assert response["X-Content-Type-Options"] == "nosniff"

    def test_serve_subject_download_unauthorized(self, student):
        paid_doc = DocumentFactory(price=5000, is_published=True)
        with pytest.raises(PermissionDenied):
            DocumentServingService.serve_subject_download(user=student, document=paid_doc)

    def test_serve_correction_inline(self, student):
        free_doc = DocumentFactory(price=0, is_published=True)
        response = DocumentServingService.serve_correction_inline(user=student, document=free_doc)
        assert isinstance(response, FileResponse)

    def test_serve_correction_inline_unauthorized(self, student):
        paid_doc = DocumentFactory(price=5000, is_published=True)
        with pytest.raises(PermissionDenied):
            DocumentServingService.serve_correction_inline(user=student, document=paid_doc)

    def test_log_access(self, student):
        doc = DocumentFactory()
        log = DocumentAccessLogService.log_access(user=student, document=doc, action=ACTION_DOWNLOAD_SUBJECT)
        assert log.pk is not None
        assert log.user == student
        assert log.document == doc
        assert log.action == ACTION_DOWNLOAD_SUBJECT
