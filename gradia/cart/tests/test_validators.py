import pytest
from django.core.exceptions import ValidationError
from gradia.cart.models import Cart
from gradia.cart.validators import (
    validate_cart_is_active,
    validate_document_exists_and_purchasable,
    validate_user_is_student,
)
from gradia.document.tests.factories import DocumentFactory
from gradia.users.tests.factories import UserFactory
from gradia.utils.enums import CartStatus


@pytest.mark.django_db
class TestCartValidators:
    def test_validate_user_is_student_valid(self, student):
        validate_user_is_student(student)

    def test_validate_user_is_student_invalid(self):
        staff = UserFactory(is_staff=True, is_student=False)
        with pytest.raises(ValidationError, match="Seuls les étudiants peuvent accéder au panier"):
            validate_user_is_student(staff)

        with pytest.raises(ValidationError, match="Seuls les étudiants peuvent accéder au panier"):
            validate_user_is_student(None)

    def test_validate_document_exists_and_purchasable_valid(self):
        doc = DocumentFactory(price=2500, is_published=True)
        retrieved = validate_document_exists_and_purchasable(doc.pk)
        assert retrieved == doc

    def test_validate_document_nonexistent(self):
        import uuid
        with pytest.raises(ValidationError, match="Le document demandé n’existe pas"):
            validate_document_exists_and_purchasable(uuid.uuid4())

    def test_validate_document_unpublished(self):
        doc = DocumentFactory(price=2500, is_published=False)
        with pytest.raises(ValidationError, match="Ce document n’est pas disponible à la vente"):
            validate_document_exists_and_purchasable(doc.pk)

    def test_validate_document_free_or_invalid_price(self):
        doc = DocumentFactory(price=0, is_published=True)
        with pytest.raises(ValidationError, match="Le prix du document est invalide"):
            validate_document_exists_and_purchasable(doc.pk)

    def test_validate_cart_is_active(self, student):
        active_cart = Cart.objects.create(student=student, status=CartStatus.ACTIVE)
        validate_cart_is_active(active_cart)

        inactive_cart = Cart.objects.create(student=UserFactory(is_student=True), status=CartStatus.ABANDONED)
        with pytest.raises(ValidationError, match="Le panier n’est pas modifiable"):
            validate_cart_is_active(inactive_cart)
