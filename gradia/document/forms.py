"""
Formulaires du module Document.

La logique métier d'achat ou d'autorisation est gérée par `gradia.document.services.DocumentAccessService`.
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from gradia.document.models import Document
from gradia.document.validators import validate_correction_file, validate_subject_file


class DocumentCreateForm(forms.ModelForm):
    """Création d'un document : les deux fichiers sont requis."""

    subject_file = forms.FileField(
        label=_("Sujet"),
        validators=[validate_subject_file],
        help_text=_("PDF, DOC ou DOCX - 25 Mo maximum."),
    )
    correction_file = forms.FileField(
        label=_("Corrigé"),
        validators=[validate_correction_file],
        help_text=_("PDF, DOC ou DOCX - 25 Mo maximum."),
    )

    class Meta:
        model = Document
        fields = [
            "title",
            "description",
            "context",
            "contest_session",
            "price",
            "subject_file",
            "correction_file",
            "is_published",
        ]
        labels = {
            "title": _("Titre"),
            "description": _("Description"),
            "context": _("Sujet (intitulé)"),
            "contest_session": _("Session de concours"),
            "price": _("Prix (FCFA)"),
            "is_published": _("Publié"),
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price") or 0
        if price < 0:
            raise forms.ValidationError(_("Le prix ne peut pas être négatif."))
        return price


class DocumentUpdateForm(forms.ModelForm):
    """
    Modification d'un document : les fichiers sont facultatifs
    (non ré-uploadés = fichiers actuels conservés).
    """

    subject_file = forms.FileField(
        label=_("Sujet"),
        required=False,
        validators=[validate_subject_file],
        help_text=_("Laissez vide pour conserver le fichier actuel."),
    )
    correction_file = forms.FileField(
        label=_("Corrigé"),
        required=False,
        validators=[validate_correction_file],
        help_text=_("Laissez vide pour conserver le fichier actuel."),
    )

    class Meta:
        model = Document
        fields = [
            "title",
            "description",
            "context",
            "contest_session",
            "price",
            "subject_file",
            "correction_file",
            "is_published",
        ]
        labels = {
            "title": _("Titre"),
            "description": _("Description"),
            "context": _("Sujet (intitulé)"),
            "contest_session": _("Session de concours"),
            "price": _("Prix (FCFA)"),
            "is_published": _("Publié"),
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price") or 0
        if price < 0:
            raise forms.ValidationError(_("Le prix ne peut pas être négatif."))
        return price