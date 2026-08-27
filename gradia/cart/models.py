from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.forms import MoneyField

from gradia.core.models import BaseModel
from gradia.utils.enums import CartStatus
from gradia.document.models import Document


class Cart(BaseModel):
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart", limit_choices_to={"is_student": True},)
    status = models.CharField(
        _("statut"), max_length=20, choices=CartStatus.choices, default=CartStatus.ACTIVE
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Panier")
        verbose_name_plural = _("Paniers")

    def __str__(self):
        return f"Panier de {self.student} ({self.get_status_display()})"

    @property
    def items_count(self) -> int:
        return self.items.count()


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, verbose_name=_("panier"), on_delete=models.CASCADE, related_name="items")
    document = models.ForeignKey(Document, verbose_name=_("document"), on_delete=models.PROTECT, related_name="cart_items")
    unit_price = MoneyField(
        _("prix unitaire figé"), max_digits=12, decimal_places=2, default_currency=settings.DEFAULT_CURRENCY
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "document"],
                name="unique_document_par_cart",
            ),
        ]
        verbose_name = _("Article du panier")
        verbose_name_plural = _("Articles du panier")

    def __str__(self):
        return f"{self.document} - {self.cart}"

    @property
    def subtotal(self):
        return self.unit_price
    
    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.document.price
        super().save(*args, **kwargs)