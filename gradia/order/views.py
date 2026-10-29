from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView

from gradia.cart.services import get_or_create_cart
from gradia.order.models import Order
from gradia.order.services import create_order_from_cart


class StudentRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_student:
            messages.error(request, _("Les commandes sont réservées aux étudiants."))
            return redirect("document:list")
        return super().dispatch(request, *args, **kwargs)


class CheckoutView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request):
        try:
            cart = get_or_create_cart(request.user)
            order = create_order_from_cart(request.user, cart)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect("cart:detail")
        messages.success(request, _("Votre commande a été créée."))
        return redirect("order:detail", pk=order.pk)


class OrderDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    template_name = "order/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return (
            Order.objects.filter(student=self.request.user)
            .prefetch_related("items__document__contest_session__contest")
            .order_by("-created_at")
        )
