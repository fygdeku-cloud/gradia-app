from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView

from gradia.cart.selectors import get_cart_for_student
from gradia.cart.services import add_document_to_cart
from gradia.cart.services import calculate_cart_total
from gradia.cart.services import get_or_create_cart
from gradia.cart.services import remove_cart_item


class StudentRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_student:
            messages.error(request, _("Le panier est réservé aux étudiants."))
            return redirect("document:list")
        return super().dispatch(request, *args, **kwargs)


class CartDetailView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    template_name = "cart/cart_detail.html"
    context_object_name = "items"

    def get_queryset(self):
        self.cart = get_or_create_cart(self.request.user)
        cart = get_cart_for_student(self.request.user)
        return cart.items.all() if cart else self.cart.items.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart_total"] = calculate_cart_total(self.cart)
        return context


class AddToCartView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request, pk):
        try:
            add_document_to_cart(request.user, pk)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
        else:
            messages.success(request, _("Document ajouté au panier."))
        return redirect("cart:detail")


class RemoveCartItemView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request, pk):
        try:
            remove_cart_item(request.user, pk)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
        else:
            messages.success(request, _("Article supprimé du panier."))
        return redirect("cart:detail")
