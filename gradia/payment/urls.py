from django.urls import path

from gradia.payment.views.payment_views import (
    PaymentCancelView,
    PaymentInitiationView,
    PaymentProcessingView,
    PaymentStatusView,
    PaymentSuccessView,
)

from gradia.payment.views.webhook_views import PaymentWebhookView
from gradia.payment.views.history_views import PaymentHistoryView

app_name = "payment"


urlpatterns = [
    # Page permettant à l'étudiant de démarrer son paiement.
    path(
        "order/<uuid:order_id>/pay/",
        PaymentInitiationView.as_view(),
        name="initiate",
    ),

    # Page affichée lorsque Stripe renvoie l'étudiant vers Gradia.
    path(
        "processing/<uuid:payment_id>/",
        PaymentProcessingView.as_view(),
        name="processing",
    ),

    # Endpoint interrogé périodiquement par la page processing.
    path(
        "status/<uuid:payment_id>/",
        PaymentStatusView.as_view(),
        name="status",
    ),

    # Page affichée après confirmation réelle du paiement.
    path(
        "success/<uuid:payment_id>/",
        PaymentSuccessView.as_view(),
        name="success",
    ),

    # Page affichée lorsqu'un paiement n'est pas confirmé.
    path(
        "cancel/<uuid:payment_id>/",
        PaymentCancelView.as_view(),
        name="cancel",
    ),

    # Endpoint public appelé par Stripe.
    path(
        "webhook/",
        PaymentWebhookView.as_view(),
        name="webhook",
    ),

    # Historique des paiements de l'utilisateur connecté.
    path(
        "history/",
        PaymentHistoryView.as_view(),
        name="history",
    ),
]