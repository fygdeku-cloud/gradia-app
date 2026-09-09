from __future__ import annotations

from typing import Optional

from django.db.models import Prefetch, QuerySet
from gradia.cart.models import Cart, CartItem


def get_user_cart(user) -> Optional[Cart]:
    """Return the Cart belonging to *user* or ``None`` if absent."""
    return Cart.objects.filter(student=user).first()


def get_cart_with_items(cart: Cart) -> Cart:
    """Prefetch items and related Document for efficient rendering."""
    return (
        Cart.objects.filter(pk=cart.pk)
        .prefetch_related(
            Prefetch(
                "items",
                queryset=CartItem.objects.select_related("document"),
            )
        )
        .first()
    )


def get_cart_items(cart: Cart) -> QuerySet[CartItem]:
    """Return cart items with the Document already selected."""
    return CartItem.objects.filter(cart=cart).select_related("document")
