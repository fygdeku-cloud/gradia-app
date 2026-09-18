from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from gradia.cart.selectors import get_cart_with_items
from gradia.cart.services import calculate_cart_totals, get_or_create_cart
from gradia.cart.permissions import StudentRequiredMixin


class CartDetailView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    template_name = "cart/cart_detail.html"
    context_object_name = "items"

    def get_queryset(self):
        cart = get_or_create_cart(self.request.user)
        return get_cart_with_items(cart).items.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_or_create_cart(self.request.user)
        context["totals"] = calculate_cart_totals(cart)
        return context
