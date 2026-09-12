from __future__ import annotations

from typing import Optional

from django.db.models import Prefetch, QuerySet
from gradia.cart.models import Cart, CartItem


def get_user_cart(user) -> Optional[Cart]:
    """Retourne le panier appartenant à *user* ou ``None`` s'il est absent."""
    return Cart.objects.filter(student=user).first()


def get_cart_with_items(cart: Cart) -> Cart:
    """Précharge les éléments et le Document associé pour un rendu efficace."""
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
    """Retourne les articles du panier avec le Document déjà sélectionné."""
    return CartItem.objects.filter(cart=cart).select_related("document")
