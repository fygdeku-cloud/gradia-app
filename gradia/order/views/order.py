from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import View
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from gradia.cart.services import get_or_create_cart
from gradia.order.services import create_order_from_cart
from gradia.order.permissions import StudentRequiredMixin


class CheckoutView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request):
        try:
            cart = get_or_create_cart(request.user)
            order = create_order_from_cart(request.user, cart)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect("cart:detail")
        
        messages.success(request, _("Commande créée avec succès."))
        return redirect("order:detail", pk=order.pk)
