from django.db.models import QuerySet
from gradia.order.models import Order

def get_user_orders(user) -> QuerySet[Order]:
    """Return orders belonging to the user."""
    return Order.objects.filter(student=user)

def get_order_detail(user, order_id: int) -> Order:
    """Return specific order for user."""
    return Order.objects.filter(student=user, pk=order_id).prefetch_related("items__document").get()
