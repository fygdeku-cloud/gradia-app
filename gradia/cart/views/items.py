from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import View
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from gradia.cart.forms import AddToCartForm
from gradia.cart.services import (
    add_document_to_cart,
    # update_cart_item,
    remove_cart_item,
    clear_cart,
)
from gradia.cart.permissions import StudentRequiredMixin
from gradia.cart.forms import AddToCartForm


class AddToCartView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = AddToCartForm(
            request.POST,
            user=request.user,
        )

        if not form.is_valid():
            messages.error(request, form.errors.get("document_id", ["Une erreur est survenue."])[0])
            return redirect("cart:detail")

        try:
            form.save()
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
        else:
            messages.success(
                request,
                _("Document ajouté au panier."),
            )

        return redirect("cart:detail")


# class UpdateCartItemView(LoginRequiredMixin, StudentRequiredMixin, View):
#     def post(self, request, item_id):
#         quantity = int(request.POST.get("quantity", 1))
#         try:
#             update_cart_item(request.user, item_id, quantity)
#             messages.success(request, _("Panier mis à jour."))
#         except ValidationError as e:
#             messages.error(request, e.messages[0])
#         return redirect("cart:detail")


class RemoveCartItemView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request, item_id):
        try:
            remove_cart_item(request.user, item_id)
            messages.success(request, _("Article supprimé du panier."))
        except ValidationError as e:
            messages.error(request, e.messages[0])
        return redirect("cart:detail")


class ClearCartView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request):
        try:
            clear_cart(request.user)
            messages.success(request, _("Panier vidé."))
        except ValidationError as e:
            messages.error(request, e.messages[0])
        return redirect("cart:detail")
