from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

from gradia.core.models import BaseModel
from gradia.order.models import Order
from gradia.utils.enums import (
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    PaymentType,
    ProcessingStatus,
)


class Payment(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
        verbose_name=_("commande"),
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("transaction parente"),
        help_text=_(
            "Référence à la transaction d'origine pour les remboursements "
            "ou annulations."
        ),
    )

    transaction_type = models.CharField(
        _("type"),
        max_length=20,
        choices=PaymentType.choices,
    )

    status = models.CharField(
        _("statut"),
        max_length=25,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )

    amount = MoneyField(
        _("montant"),
        max_digits=12,
        decimal_places=2,
    )

    refunded_amount = MoneyField(
        _("montant remboursé"),
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    method = models.CharField(
        _("moyen de paiement"),
        max_length=20,
        choices=PaymentMethod.choices,
    )

    provider = models.CharField(
        _("fournisseur de paiement"),
        max_length=50,
        choices=PaymentProvider.choices,
        help_text=_("Exemple : Stripe, Flutterwave, MTN, Orange."),
    )

    provider_reference = models.CharField(
        _("référence fournisseur"),
        max_length=200,
        blank=True,
        help_text=_(
            "Référence utilisée pour identifier la transaction "
            "auprès du fournisseur."
        ),
    )

    provider_transaction_id = models.CharField(
        _("ID de transaction fournisseur"),
        max_length=200,
        blank=True,
        db_index=True,
        help_text=_(
            "Identifiant de transaction fourni par le prestataire."
        ),
    )

    provider_response = models.JSONField(
        _("réponse du fournisseur"),
        default=dict,
        blank=True,
    )

    initiated_at = models.DateTimeField(
        _("date d'initiation"),
        auto_now_add=True,
    )

    processed_at = models.DateTimeField(
        _("date de traitement"),
        null=True,
        blank=True,
    )

    # Motif d'échec ou de fraude.
    failure_reason = models.TextField(
        _("motif d'échec"),
        blank=True,
    )

    notes = models.TextField(
        _("notes"),
        blank=True,
    )

    # Informations complémentaires.
    metadata = models.JSONField(
        _("métadonnées"),
        default=dict,
        blank=True,
    )

    class Meta:
        verbose_name = _("transaction de paiement")
        verbose_name_plural = _("transactions de paiement")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.get_transaction_type_display()} "
            f"#{self.pk} - {self.amount} "
            f"({self.get_status_display()})"
        )


class PaymentWebhookEvent(BaseModel):

    provider = models.CharField(
        _("fournisseur"),
        max_length=50,
        choices=PaymentProvider.choices,
    )

    # Identifiant unique de l'événement chez le fournisseur.
    event_id = models.CharField(
        _("identifiant de l'événement"),
        max_length=255,
    )

    event_type = models.CharField(
        _("type d'événement"),
        max_length=255,
    )

    # Payload complet reçu et vérifié.
    payload = models.JSONField(
        _("payload"),
        default=dict,
    )

    # Signature Stripe reçue dans l'en-tête.
    signature = models.TextField(
        _("signature"),
        blank=True,
    )

    # Adresse IP ayant envoyé la requête.
    remote_address = models.GenericIPAddressField(
        _("adresse IP"),
        null=True,
        blank=True,
    )

    received_at = models.DateTimeField(
        _("date de réception"),
        auto_now_add=True,
    )

    processed_at = models.DateTimeField(
        _("date de traitement"),
        null=True,
        blank=True,
    )

    processing_status = models.CharField(
        _("statut de traitement"),
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
        db_index=True,
    )

    error_message = models.TextField(
        _("message d'erreur"),
        blank=True,
    )

    class Meta:
        verbose_name = _("événement webhook")
        verbose_name_plural = _("événements webhook")
        ordering = ["-received_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"],
                name="unique_payment_webhook_event",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider} - {self.event_type} - {self.event_id}"
        
        