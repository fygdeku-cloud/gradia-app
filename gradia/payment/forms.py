        
from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from gradia.payment.validators import validate_payment_method_and_provider
from gradia.utils.enums import PaymentMethod, PaymentProvider


class PaymentInitiationForm(forms.Form):
    """
    Formulaire de sélection du moyen et du fournisseur de paiement.

    Le montant n'est pas un champ du formulaire :
    il est toujours déterminé côté serveur depuis Order.total_amount.
    """

    method = forms.ChoiceField(
        label=_("Moyen de paiement"),
        choices=PaymentMethod.choices,
    )

    provider = forms.ChoiceField(
        label=_("Fournisseur de paiement"),
        choices=PaymentProvider.choices,
    )

    def clean(self):
        """
        Vérifie la cohérence entre le moyen de paiement
        et le fournisseur sélectionné.
        """
        # Récupère les données validées par Django.
        cleaned_data = super().clean()
        # Récupère le moyen choisi.
        method = cleaned_data.get("method")
        # Récupère le fournisseur choisi.
        provider = cleaned_data.get("provider")

        # Si un champ est absent, son propre validateur
        # affichera l'erreur appropriée.
        if not method or not provider:
            return cleaned_data

        # Réutilise la règle métier centrale afin d'éviter d'avoir une deuxième implémentation dans le formulaire.
        validate_payment_method_and_provider(
            method=method,
            provider=provider,
        )

        # Retourne les données nettoyées.
        return cleaned_data