from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

# ORDER ENUMS

class OrderStatus(models.TextChoices):
        PENDING = "PENDING", _("En attente")
        SUCCESS = "SUCCESS", _("Success")
        FAILED = "FAILED", _("Échouée")
        CANCELLED = "CANCELLED", _("Annulée")

# PAYMENT ENUMS

class PaymentType(models.TextChoices):
    """Type of financial operation — replaces the old TransactionType."""

    CHARGE = "charge", _("Charge")
    REFUND = "refund", _("Refund")
    PARTIAL_REFUND = "partial_refund", _("Partial Refund")


class PaymentStatus(models.TextChoices):
    """Unified status for a PaymentTransaction — merges PaymentStatus + TransactionStatus."""

    PENDING = "pending", _("Pending")
    SUCCESS = "success", _("Success")
    FAILED = "failed", _("Failed")
    CANCELLED = "cancelled", _("Cancelled")
    REFUNDED = "refunded", _("Refunded")
    PARTIALLY_REFUNDED = "partially_refunded", _("Partially Refunded")
    FRAUD = "fraud", _("Fraud")


class PaymentMethod(models.TextChoices):
    MOBILE_MONEY = "mobile_money", _("Mobile Money")
    CARD = "card", _("Bank Card")


class PaymentProvider(models.TextChoices):
    """Payment service providers for checkout."""

    STRIPE = "stripe", _("Stripe (Card)")
    FLUTTERWAVE_MOBILE_MONEY = "flutterwave_mobile_money", _("Flutterwave Mobile Money")


# CART ENUMS

class CartStatus(models.TextChoices):
        ACTIVE = "active", "Actif"
        CONVERTED = "converted", "Converti"
        ABANDONED = "abandoned", "Abandonné"

# DOCUMENTS ENUMS

ACTION_VIEW_CORRECTION = "view_correction"
ACTION_DOWNLOAD_SUBJECT = "download_subject"

ACTION_CHOICES = [
    (
        ACTION_VIEW_CORRECTION,
        "Consultation de la correction",
    ),
    (
        ACTION_DOWNLOAD_SUBJECT,
        "Téléchargement du sujet",
    ),
]

# SPPORT ENUMS

class Priority(models.TextChoices):
        LOW = "low", _("Faible")
        MEDIUM = "medium", _("Moyenne")
        HIGH = "high", _("Élevée")
        URGENT = "urgent", _("Urgente")