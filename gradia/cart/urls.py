from django.urls import path

from gradia.cart.views import AddToCartView
from gradia.cart.views import CartDetailView
from gradia.cart.views import RemoveCartItemView

app_name = "cart"

urlpatterns = [
    path("", CartDetailView.as_view(), name="detail"),
    path("add/<uuid:pk>/", AddToCartView.as_view(), name="add"),
    path("remove/<uuid:pk>/", RemoveCartItemView.as_view(), name="remove"),
]
