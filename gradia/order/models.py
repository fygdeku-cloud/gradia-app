from __future__ import annotations


from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

from gradia.core.models import BaseModel
from gradia.utils.enums import OrderStatus

class Order(BaseModel):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("etudiant"),on_delete=models.PROTECT, related_name="orders")
    order_number = models.CharField(_("numéro de commande"), max_length=50, unique=True, db_index=True)
    total_amount = MoneyField(
        _("montant total"), max_digits=12, decimal_places=2, default_currency=settings.DEFAULT_CURRENCY
    )
    status = models.CharField(
        _("statut"), max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Commande")
        verbose_name_plural = _("Commandes")
        # Amelioration des filtres
        indexes = [
            models.Index(fields=["student", "status"]),
        ]

    def __str__(self):
        return self.order_number


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    document = models.ForeignKey( "document.Document", on_delete=models.PROTECT, related_name="order_items")
    unit_price = MoneyField(
        verbose_name=_("Unit price"),
        help_text=_("Original price per unit (before discount), computed from catalog at order time."),
    )
    unit_discount = MoneyField(
        default=0,
        verbose_name=_("Unit discount"),
        help_text=_(
            "Discount per unit. For a product: the product's active discount at order time. "
            "For a pack: the sum of per-unit discounts from every product inside the pack.",
        ),
    )
    quantity = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("Quantity"),
    )
    line_subtotal = MoneyField(
        default=0,
        verbose_name=_("Line subtotal"),
        help_text=_("Subtotal for this line before discount: unit_price x quantity."),
    )
    line_discount = MoneyField(
        default=0,
        verbose_name=_("Line discount"),
        help_text=_("Total discount for this line: unit_discount x quantity."),
    )
    line_total = MoneyField(
        verbose_name=_("Line total"),
        help_text=_("Total for this line after discount: line_subtotal - line_discount."),
    )
     
    class Meta:
        ordering = ["id_order_item"]
        verbose_name = "Article de commande"
        verbose_name_plural = "Articles de commande"

    def __str__(self):
        return f"{self.document} - {self.order.order_number}"