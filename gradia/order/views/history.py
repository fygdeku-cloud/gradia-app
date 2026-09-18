from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView

from gradia.order.selectors import get_user_orders, get_order_detail
from gradia.order.permissions import StudentRequiredMixin


class OrderListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    template_name = "order/order_list.html"
    context_object_name = "orders"

    def get_queryset(self):
        return get_user_orders(self.request.user)


class OrderDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    template_name = "order/order_detail.html"
    context_object_name = "order"

    def get_object(self, queryset=None):
        return get_order_detail(self.request.user, self.kwargs["pk"])
