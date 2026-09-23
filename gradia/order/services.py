from __future__ import annotations

import uuid
from djmoney.money import Money
from django.db import transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from gradia.order.models import Order, OrderItem
from gradia.cart.models import Cart
from gradia.utils.enums import OrderStatus, CartStatus

def create_order_from_cart(user, cart: Cart) -> Order:
    """
    Transforme le panier en commande.
    1. Vérifier que le panier appartient à l'utilisateur.
    2. Vérifier que le panier n'est pas vide.
    3. Calculer les totaux.
    4. Création atomique de la commande et des articles de commande.
    5. Mettre à jour le statut du panier.
    """
    if cart.student != user:
        raise ValidationError("Panier invalide.")

    items = cart.items.select_related("document").all()
    if not items.exists():
        raise ValidationError("Le panier est vide.")

    # Calculer le total
    total_amount = sum((item.unit_price.amount for item in items), Money(0, settings.DEFAULT_CURRENCY))

    with transaction.atomic():
        # Créer la commande
        order = Order.objects.create(
            student=user,
            order_number=f"ORD-{uuid.uuid4().hex[:12].upper()}", # Numéro de commande simplifié
            total_amount=total_amount,
            status=OrderStatus.PENDING,
        )

        # Créer les articles de commande
        for item in items:
            OrderItem.objects.create(
                order=order,
                document=item.document,
                unit_price=item.unit_price,
                quantity=1, # Par défaut selon la règle métier
                line_subtotal=item.unit_price,
                line_total=item.unit_price,
            )
        
        # Mettre à jour le panier
        cart.status = CartStatus.ACTIVE
        cart.items.all().delete() # Optionnel : vider les articles du panier

    return order
