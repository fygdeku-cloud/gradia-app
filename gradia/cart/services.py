from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from djmoney.money import Money

from gradia.cart.models import Cart
from gradia.cart.models import CartItem
from gradia.document.models import Document
from gradia.document.selectors import has_confirmed_payment
from gradia.utils.enums import CartStatus


def get_or_create_cart(student):
    if not student.is_authenticated or not student.is_student:
        raise ValidationError(_("Seuls les étudiants peuvent utiliser le panier."))
    cart = Cart.objects.get_or_create(student=student)[0]
    if cart.status != CartStatus.ACTIVE:
        cart.status = CartStatus.ACTIVE
        cart.save(update_fields=["status", "updated_at"])
    return cart


def add_document_to_cart(student, document_id):
    if not student.is_authenticated or not student.is_student:
        raise ValidationError(_("Seuls les étudiants peuvent utiliser le panier."))
    document = Document.objects.filter(pk=document_id, is_published=True).first()
    if document is None or document.price <= 0:
        raise ValidationError(_("Ce document n'est pas disponible à l'achat."))
    if has_confirmed_payment(student, document):
        raise ValidationError(_("Ce document est déjà accessible dans vos achats."))
    cart = get_or_create_cart(student)
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        document=document,
        defaults={"unit_price": Money(document.price, settings.DEFAULT_CURRENCY)},
    )
    if not created:
        raise ValidationError(_("Ce document se trouve déjà dans votre panier."))
    return item


def remove_cart_item(student, item_id):
    item = CartItem.objects.filter(pk=item_id, cart__student=student).first()
    if item is None:
        raise ValidationError(_("Cet article n'existe pas dans votre panier."))
    item.delete()


def calculate_cart_total(cart):
    items = list(cart.items.select_related("document"))
    if not items:
        return Money(Decimal("0.00"), settings.DEFAULT_CURRENCY)
    return sum(
        (item.unit_price for item in items),
        Money(Decimal("0.00"), items[0].unit_price.currency),
    )
