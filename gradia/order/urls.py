from django.urls import path

from gradia.order.views import CheckoutView
from gradia.order.views import OrderDetailView

app_name = "order"

urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("<uuid:pk>/", OrderDetailView.as_view(), name="detail"),
]
