from django.urls import path
from gradia.order.views import OrderListView, OrderDetailView, CheckoutView

app_name = "order"

urlpatterns = [
    path("", OrderListView.as_view(), name="list"),
    path("<uuid:pk>/", OrderDetailView.as_view(), name="detail"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
]
