# Importe path pour définir les routes Django.
from django.urls import path

# Importe la vue d'initiation du paiement.
from gradia.payment.views.payment_views import PaymentInitiationView

# Importe la vue de webhook utilisée par le fournisseur de paiement.
from gradia.payment.views.webhook_views import PaymentWebhookView

# Importe la vue d'historique des paiements.
from gradia.payment.views.history_views import PaymentHistoryView


# Namespace de l'application Payment.
# Il permettra d'utiliser par exemple "payment:history" dans les templates.
app_name = "payment"


# Déclare toutes les URLs du module Payment.
urlpatterns = [
    # Affiche le formulaire et initialise le paiement d'une commande.
    # Exemple : /payment/order/<uuid>/pay/
    path(
        "order/<uuid:order_id>/pay/",
        PaymentInitiationView.as_view(),
        name="initiate",
    ),

    # Reçoit les notifications serveur-à-serveur du fournisseur.
    # Cette URL sera appelée directement par Stripe ou Flutterwave.
    path(
        "webhook/",
        PaymentWebhookView.as_view(),
        name="webhook",
    ),

    # Affiche l'historique des paiements de l'étudiant connecté.
    path(
        "history/",
        PaymentHistoryView.as_view(),
        name="history",
    ),
]