from django.db import models

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from gradia.core.models import BaseModel, TitleDescriptionModel
from gradia.utils.enums import Priority

class SupportRequest(BaseModel, TitleDescriptionModel):
    # Représente une demande d'assistance envoyée par un utilisateur.
    # Une demande peut contenir plusieurs SupportMessage.
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_requests",
        verbose_name=_("Étudiant"),
        help_text=_("Utilisateur à l'origine de la demande."),
    )
    status = models.BooleanField(
        default=True,
        verbose_name=_("Statut"),
        help_text=_(
            "Indique si la demande est ouverte (True) ou fermée (False)."
        ),
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_("Priorité"),
    )

    class Meta:
        ordering = ["-created_at"]

        verbose_name = _("Demande de support")
        verbose_name_plural = _("Demandes de support")

        indexes = [
            models.Index(
                fields=["student", "-created_at"],
                name="supp_stud_date_id",
            ),
            models.Index(
                fields=["status", "-created_at"],
                name="supp_req_stat_date_id",
            ),
            models.Index(
                fields=["priority", "status"],
                name="supp_req_prio_stat_id",
            ),
        ]

    def __str__(self):
        return _(
            "Demande de %(username)s - %(id)s"
        ) % {
            "username": self.student.name,
            "id": str(self.id)[:8],
        }

    @property
    def is_open(self):
        """
        Retourne True si la demande est ouverte.
        """
        return self.status

    @property
    def is_closed(self):
        """
        Retourne True si la demande est fermée.
        """
        return not self.status

    def close(self):
        """
        Ferme la demande de support.
        """
        if self.status:
            self.status = False
            self.save(update_fields=["status"])

    def reopen(self):
        """
        Réouvre une demande précédemment fermée.
        """
        if not self.status:
            self.status = True
            self.save(update_fields=["status"])

    def set_priority(self, priority):
        """
        Modifie la priorité de la demande.
        """
        valid_priorities = self.Priority.values

        if priority not in valid_priorities:
            raise ValueError(
                _("Priorité de support invalide.")
            )

        if self.priority != priority:
            self.priority = priority
            self.save(update_fields=["priority"])

    def get_messages(self):
        """
        Retourne les messages de la demande dans l'ordre chronologique.
        """
        return self.messages.select_related("sender").all()

    def get_last_message(self):
        """
        Retourne le dernier message de la demande.
        """
        return (
            self.messages
            .select_related("sender")
            .order_by("-created_at")
            .first()
        )

    def add_message(self, sender, message):
        """
        Ajoute un nouveau message à la demande.

        Cette méthode reste volontairement simple.
        Les règles métier plus complexes peuvent être placées
        dans support/services.py.
        """
        if not self.status:
            raise ValueError(
                _("Impossible d'ajouter un message à une demande fermée.")
            )

        if not message or not message.strip():
            raise ValueError(
                _("Le message ne peut pas être vide.")
            )

        return self.messages.create(
            sender=sender,
            message=message.strip(),
        )


class SupportMessage(BaseModel):
    """
    Représente un message appartenant à une demande de support.
    """
    support_request = models.ForeignKey(
        SupportRequest,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Demande de support"),
        help_text=_("Demande de support à laquelle appartient le message."),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_messages",
        verbose_name=_("Expéditeur"),
        help_text=_("Utilisateur ayant envoyé le message."),
    )

    message = models.TextField(
        verbose_name=_("Message"),
        help_text=_("Contenu du message."),
    )

    class Meta:
        ordering = ["created_at"]

        verbose_name = _("Message de support")
        verbose_name_plural = _("Messages de support")

        indexes = [
            models.Index(
                fields=["support_request", "created_at"],
                name="support_msg_request_date_idx",
            ),
            models.Index(
                fields=["sender", "-created_at"],
                name="support_msg_sender_date_idx",
            ),
        ]

    def __str__(self):
        return _(
            "Message de %(username)s - %(date)s"
        ) % {
            "username": self.sender.username,
            "date": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }

    @property
    def is_from_admin(self):
        """
        Indique si le message a été envoyé par un administrateur.
        """
        return getattr(self.sender, "is_admin", False)

    @property
    def is_from_student(self):
        """
        Indique si le message a été envoyé par un étudiant.
        """
        return getattr(self.sender, "is_student", False)
