from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from requests import request

from gradia.cart.models import Cart, CartItem
from gradia.cart.selectors import get_cart_items
from gradia.cart.validators import (
    validate_user_is_student,
    validate_document_exists_and_purchasable,
    validate_cart_is_active,
)
from gradia.utils.enums import CartStatus

def get_cart(user) -> Optional[Cart]:
    """Return the active cart for *user* or ``None``.

    The caller should handle ``None`` (e.g., treat as empty cart).
    """
    validate_user_is_student(user)
    return get_or_create_cart(user)


def get_or_create_cart(user) -> Cart:
    """Retrieve the existing cart for *user* or create a new one (ACTIVE)."""
    cart, _ = Cart.objects.get_or_create(
        student=user,
        defaults={"status": CartStatus.ACTIVE},
    )
    validate_cart_is_active(cart)
    return cart

def add_document_to_cart(user, document_id: int) -> CartItem:
    """Add a document to the user's cart.

    - Ensures the user is a student.
    - Validates the document exists and is purchasable.
    - Retrieves or creates the active cart.
    - If the document is already in the cart, raises ``ValidationError``.
    - Stores the current price from the Document as ``unit_price`` (snapshot).
    """
    validate_user_is_student(user)
    document = validate_document_exists_and_purchasable(document_id)
    cart = get_or_create_cart(request.user)
    validate_cart_is_active(cart)

    if CartItem.objects.filter(cart=cart, document=document).exists():
        raise ValidationError("Le document est déjà présent dans le panier.")

    with transaction.atomic():
        item = CartItem.objects.create(cart=cart, document=document)
        return item

# def update_cart_item(user, item_id: int, quantity: int) -> CartItem:
#     """Update the quantity of a cart item.

#     The current model does not store ``quantity`` (items are unique per document),
#     but the function is kept for future extensibility. For now, we only allow
#     ``quantity`` of ``1``; any other value raises ``ValidationError``.
#     """
#     validate_user_is_student(user)
#     if quantity != 1:
#         raise ValidationError("La quantité doit être 1 pour ce produit.")
#     try:
#         item = CartItem.objects.select_related('cart').get(pk=item_id)
#     except CartItem.DoesNotExist:
#         raise ValidationError("L'article du panier n'existe pas.")
#     if item.cart.student != user:
#         raise ValidationError("Vous n'êtes pas autorisé à modifier cet article.")
#     validate_cart_is_active(item.cart)
#     return item

def remove_cart_item(user, item_id: int) -> None:
    """Remove a cart item belonging to *user*.
    """
    validate_user_is_student(user)
    try:
        item = CartItem.objects.select_related('cart').get(pk=item_id)
    except CartItem.DoesNotExist:
        raise ValidationError("L'article du panier n'existe pas.")
    if item.cart.student != user:
        raise ValidationError("Vous n'êtes pas autorisé à supprimer cet article.")
    validate_cart_is_active(item.cart)
    item.delete()

def clear_cart(user) -> None:
    """Delete all items from the user's active cart.
    """
    validate_user_is_student(user)
    cart = get_or_create_cart(user)
    validate_cart_is_active(cart)
    CartItem.objects.filter(cart=cart).delete()

def calculate_cart_totals(cart: Cart) -> dict:
    """Return a dict with ``subtotal`` and ``total`` for *cart*.

    Currently, no extra fees are applied, so ``total`` == ``subtotal``.
    """
    subtotal = (
        CartItem.objects.filter(cart=cart)
        .aggregate(total=Sum('unit_price'))
        .get('total')
        or Decimal('0.00')
    )
    return {'subtotal': subtotal, 'total': subtotal}
