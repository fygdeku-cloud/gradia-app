from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError
from gradia.cart.models import CartItem
from gradia.cart.services import add_document_to_cart
from gradia.cart.validators import validate_document_exists_and_purchasable


class AddToCartForm(forms.Form):
    """Form displayed on a document detail page.
    It validates *only* that the document exists and is purchasable.
    The mutation (creation of the CartItem) is performed explicitly via the
    ``save`` method, called from the view after the form is valid.
    """

    document_id = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_document_id(self) -> int:
        doc_id = self.cleaned_data["document_id"]
        # La validation ne modifie PAS le panier.
        try:
            validate_document_exists_and_purchasable(doc_id)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages)
        return doc_id

    def save(self):
        """Create the CartItem after the form has been validated."""
        return add_document_to_cart(self.user, self.cleaned_data["document_id"])
