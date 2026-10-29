import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from djmoney.money import Money

from gradia.order.models import Order
from gradia.order.models import OrderItem
from gradia.utils.enums import CartStatus
from gradia.utils.enums import OrderStatus


@transaction.atomic
def create_order_from_cart(student, cart) -> Order:
    if cart.student_id != student.pk or cart.status != CartStatus.ACTIVE:
        raise ValidationError(_("Ce panier ne peut pas être converti en commande."))

    items = list(cart.items.select_for_update().select_related("document"))
    if not items:
        raise ValidationError(_("Votre panier est vide."))

    currency = items[0].unit_price.currency
    total = Money(Decimal("0.00"), currency)
    for item in items:
        if not item.document.is_published:
            raise ValidationError(_("Un document du panier n'est plus disponible."))
        total += item.unit_price

    order = Order.objects.create(
        student=student,
        order_number=f"GR-{uuid.uuid4().hex[:12].upper()}",
        total_amount=total,
        status=OrderStatus.PENDING,
    )
    zero = Money(Decimal("0.00"), currency)
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                document=item.document,
                unit_price=item.unit_price,
                unit_discount=zero,
                quantity=1,
                line_subtotal=item.unit_price,
                line_discount=zero,
                line_total=item.unit_price,
            )
            for item in items
        ],
    )
    cart.items.all().delete()
    cart.status = CartStatus.CONVERTED
    cart.save(update_fields=["status", "updated_at"])
    return order
