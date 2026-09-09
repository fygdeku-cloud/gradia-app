from __future__ import annotations

import uuid
from djmoney.money import Money
from django.db import transaction
from django.core.exceptions import ValidationError
from config import settings
from gradia.order.models import Order, OrderItem
from gradia.cart.models import Cart
from gradia.utils.enums import OrderStatus, CartStatus

def create_order_from_cart(user, cart: Cart) -> Order:
    """
    Transform cart into order.
    1. Verify cart belongs to user.
    2. Check cart not empty.
    3. Calculate totals.
    4. Atomic creation of Order and OrderItems.
    5. Update cart status.
    """
    if cart.student != user:
        raise ValidationError("Panier invalide.")

    items = cart.items.select_related("document").all()
    if not items.exists():
        raise ValidationError("Le panier est vide.")

    # Calculate total
    total_amount = sum((item.unit_price.amount for item in items), Money(0, settings.DEFAULT_CURRENCY))

    with transaction.atomic():
        # Create order
        order = Order.objects.create(
            student=user,
            order_number=f"ORD-{uuid.uuid4().hex[:12].upper()}", # Simplistic order number
            total_amount=total_amount,
            status=OrderStatus.PENDING,
        )

        # Create OrderItems
        for item in items:
            OrderItem.objects.create(
                order=order,
                document=item.document,
                unit_price=item.unit_price,
                quantity=1, # Default as per business rule
                line_subtotal=item.unit_price,
                line_total=item.unit_price,
            )
        
        # Update cart
        cart.status = CartStatus.ACTIVE
        cart.items.all().delete() # Optional: clear cart items

    return order
