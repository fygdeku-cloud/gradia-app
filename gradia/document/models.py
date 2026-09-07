from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from gradia.core.models import BaseModel, TitleDescriptionModel
from gradia.document.storages import protected_document_storage
from gradia.utils.enums import ACTION_CHOICES


""" FONCTIONS UTILITAIRES INDIQUANT OU JE VAIS ENREGISTRER LES FICHIERS UPLOADEES"""

def document_subject_upload_path(instance, filename):
    return (
        f"documents/"
        f"{instance.contest_session.contest.slug}/"
        f"{instance.contest_session.year}/"
        f"subjects/"
        f"{filename}"
    )

def document_correction_upload_path(instance, filename):
    return (
        f"documents/"
        f"{instance.contest_session.contest.slug}/"
        f"{instance.contest_session.year}/"
        f"corrections/"
        f"{filename}"
    )


class Document(BaseModel, TitleDescriptionModel):
    subject_file = models.FileField(
        _("Subject File"),
        upload_to=document_subject_upload_path,
        storage=protected_document_storage,
        help_text=_("PDF or DOCX file."),
    )
    correction_file = models.FileField(
        _("Correction File"),
        upload_to=document_correction_upload_path,
        storage=protected_document_storage,
        help_text=_("PDF or DOCX file."),
    )
    price = models.PositiveIntegerField(default=0)
    context = models.CharField(_("Subject"), max_length=255, blank=True)
    contest_session = models.ForeignKey("contest.ContestSession", on_delete=models.CASCADE, related_name="documents")
    is_published = models.BooleanField(
        _("Published"),
        default=True,
        help_text=_(
            "Seuls les documents publiés sont visibles dans le catalogue "
            "et consultables par les étudiants."
        ),
    )

    class Meta:
        ordering = ["title"]
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("document:detail", kwargs={"pk": self.pk})

    def has_correction(self):
        return bool(self.correction_file)


class DocumentAccessLog(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name = _("User"), on_delete=models.CASCADE, related_name="document_access_logs", null=True, blank=True)
    document = models.ForeignKey(Document, verbose_name = _("Document"), on_delete=models.CASCADE, related_name="access_logs")
    action = models.CharField(_("Action"), max_length=50, choices=ACTION_CHOICES)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-accessed_at"]
        verbose_name = _("Journal d'accès au document")
        verbose_name_plural = _("Journaux d'accès aux documents")

    def __str__(self):
        return f"{self.document.title} - {self.get_action_display()}"