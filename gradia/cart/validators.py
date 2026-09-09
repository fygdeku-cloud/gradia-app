from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from gradia.document.models import Document
from gradia.utils.enums import CartStatus


def validate_user_is_student(user) -> None:
    """Raise ValidationError if ``user`` is not marked as a student."""
    if (user is None or  not user.is_authenticated or not getattr(user, "is_student", False)):
        raise ValidationError(_("Seuls les étudiants peuvent accéder au panier."))


def validate_document_exists_and_purchasable(document_id: int) -> Document:
    """Return the ``Document`` instance if it exists, is published and has a valid price.
    Raises ``ValidationError`` otherwise.
    """
    try:
        doc = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        raise ValidationError(_("Le document demandé n’existe pas."))

    if not doc.is_published:
        raise ValidationError(_("Ce document n’est pas disponible à la vente."))

    if doc.price is None or doc.price <= 0:
        raise ValidationError(_("Le prix du document est invalide."))

    return doc


def validate_cart_is_active(cart) -> None:
    """Ensure the cart's ``status`` is ``CartStatus.ACTIVE`` before mutating it."""
    if cart.status != CartStatus.ACTIVE:
        raise ValidationError(
            _("Le panier n’est pas modifiable (statut : %(status)s).")
            % {"status": cart.get_status_display()}
        )
