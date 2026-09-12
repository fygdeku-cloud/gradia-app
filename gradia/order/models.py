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
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Prix unitaire"),
        help_text=_("Prix original par unité (avant remise), calculé depuis le catalogue au moment de la commande."),
    )
    unit_discount = MoneyField(
        default=0,
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Remise unitaire"),
        help_text=_(
            "Remise par unité. Pour un produit : la remise active du produit au moment de la commande. "
            "Pour un pack : la somme des remises par unité de chaque produit à l'intérieur du pack.",
        ),
    )
    quantity = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("Quantité"),
    )
    line_subtotal = MoneyField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Sous-total de la ligne"),
        help_text=_("Sous-total pour cette ligne avant remise : prix unitaire x quantité."),
    )
    line_discount = MoneyField(
        default=0,
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Remise de la ligne"),
        help_text=_("Remise totale pour cette ligne : remise unitaire x quantité."),
    )
    line_total = MoneyField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Total de la ligne"),
        help_text=_("Total pour cette ligne après remise : sous-total de la ligne - remise de la ligne."),
    )
     
    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Article de commande")
        verbose_name_plural = _("Articles de commande")

    def __str__(self):
        return f"{self.document} - {self.order.order_number}"