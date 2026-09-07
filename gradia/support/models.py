from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from gradia.core.models import BaseModel, TitleDescriptionModel
from gradia.utils.enums import Priority, TicketStatus

class Ticket(BaseModel, TitleDescriptionModel):
    # Représente une demande d'assistance envoyée par un utilisateur.
    # Une demande peut contenir plusieurs TicketMessage.
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets",
        verbose_name=_("Étudiant"),
        help_text=_("Utilisateur à l'origine du ticket."),
    )
    status = models.CharField(
        max_length=20,
        choices=TicketStatus.choices,
        default=TicketStatus.OPEN,
        verbose_name=_("Statut"),
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_("Priorité"),
    )

    class Meta:
        ordering = ["-created_at"]

        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")

        indexes = [
            models.Index(
                fields=["student", "-created_at"],
                name="ticket_stud_date_id",
            ),
            models.Index(
                fields=["status", "-created_at"],
                name="ticket_stat_date_id",
            ),
            models.Index(
                fields=["priority", "status"],
                name="ticket_prio_stat_id",
            ),
        ]

    def __str__(self):
        return _(
            "Ticket de %(username)s - %(id)s"
        ) % {
            "username": self.student.name,
            "id": str(self.id)[:8],
        }

    @property
    def is_open(self):
        return self.status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]

    @property
    def is_closed(self):
        return self.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]

    def close(self):
        if not self.is_closed:
            self.status = TicketStatus.CLOSED
            self.save(update_fields=["status"])

    def reopen(self):
        if self.is_closed:
            self.status = TicketStatus.OPEN
            self.save(update_fields=["status"])

    def set_priority(self, priority):
        if priority not in Priority.values:
            raise ValueError(
                _("Priorité de support invalide.")
            )

        if self.priority != priority:
            self.priority = priority
            self.save(update_fields=["priority"])

    def get_messages(self):
        return self.messages.select_related("sender").all()

    def get_last_message(self):
        return (
            self.messages
            .select_related("sender")
            .order_by("-created_at")
            .first()
        )

    def add_message(self, sender, message):
        if self.is_closed:
            raise ValueError(
                _("Impossible d'ajouter un message à un ticket fermé.")
            )

        if not message or not message.strip():
            raise ValueError(
                _("Le message ne peut pas être vide.")
            )

        return self.messages.create(
            sender=sender,
            message=message.strip(),
        )


class TicketMessage(BaseModel):
    """
    Représente un message appartenant à un ticket.
    """
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Ticket"),
        help_text=_("Ticket auquel appartient le message."),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_messages",
        verbose_name=_("Expéditeur"),
        help_text=_("Utilisateur ayant envoyé le message."),
    )

    message = models.TextField(
        verbose_name=_("Message"),
        help_text=_("Contenu du message."),
    )

    class Meta:
        ordering = ["created_at"]

        verbose_name = _("Message de ticket")
        verbose_name_plural = _("Messages de ticket")

        indexes = [
            models.Index(
                fields=["ticket", "created_at"],
                name="ticket_msg_ticket_date_idx",
            ),
            models.Index(
                fields=["sender", "-created_at"],
                name="ticket_msg_sender_date_idx",
            ),
        ]

    def __str__(self):
        return _(
            "Message de %(username)s - %(date)s"
        ) % {
            "username": self.sender.username,
            "date": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }
