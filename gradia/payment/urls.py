from django.urls import path

from gradia.payment.views.payment_views import PaymentInitiationView
from gradia.payment.views.webhook_views import PaymentWebhookView
from gradia.payment.views.history_views import PaymentHistoryView

app_name = "payment"


urlpatterns = [

    path(
        "order/<uuid:order_id>/pay/",
        PaymentInitiationView.as_view(),
        name="initiate",
    ),

    path(
        "webhook/",
        PaymentWebhookView.as_view(),
        name="webhook",
    ),

    path(
        "history/",
        PaymentHistoryView.as_view(),
        name="history",
    ),
]