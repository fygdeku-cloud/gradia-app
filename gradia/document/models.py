from django.conf import settings
from django.db import models
from django.urls import reverse
from gradia.core.models import BaseModel, TitleDescriptionModel
from gradia.utils.enums import ACTION_CHOICES
from django.utils.translation import gettext_lazy as _


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
    subject_file = models.FileField(upload_to=document_subject_upload_path)
    correction_file = models.FileField(upload_to=document_correction_upload_path)
    price = models.PositiveIntegerField(default=0)
    subject = models.CharField(max_length=255, blank=True)
    contest_session = models.ForeignKey("contest.ContestSession", on_delete=models.CASCADE, related_name="documents")
   
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="document_access_logs", null=True, blank=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="access_logs")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-accessed_at"]
        verbose_name = _("Journal d'accès au document")
        verbose_name_plural = _("Journaux d'accès aux documents")

    def __str__(self):
        return f"{self.document.title} - {self.get_action_display()}"