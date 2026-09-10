        
from __future__ import annotations

import json

from django.http import HttpResponse, JsonResponse
from django.views import View


class PaymentWebhookView(View):
    """
    Point d'entrée générique pour les webhooks des fournisseurs.

    La vérification cryptographique et l'interprétation du payload
    seront adaptées au fournisseur utilisé.
    """

    # Un webhook fournisseur ne doit pas être protégé par
    # l'authentification classique de l'utilisateur.
    #
    # Sa sécurité repose sur la vérification de la signature
    # envoyée par le fournisseur.
    authentication_required = False

    def post(self, request):
        """
        Reçoit une notification serveur-à-serveur du fournisseur.
        """

        # Récupère le corps brut de la requête.
        payload = request.body

        # Refuse un webhook vide.
        if not payload:
            return JsonResponse(
                {"detail": "Empty webhook payload."},
                status=400,
            )

        try:
            # Transforme le JSON reçu en dictionnaire Python.
            data = json.loads(payload)
        except json.JSONDecodeError:
            # Un webhook qui n'est pas un JSON valide est rejeté.
            return JsonResponse(
                {"detail": "Invalid JSON payload."},
                status=400,
            )

        # IMPORTANT :
        # La signature du fournisseur devra être vérifiée ici
        # avant de faire confiance aux données reçues.
        #
        # Nous ne faisons volontairement pas encore cette
        # vérification car son implémentation dépend du fournisseur.

        # À ce stade, aucune transaction Payment n'est modifiée.
        #
        # Le traitement métier sera ajouté dans un service dédié,
        # par exemple PaymentWebhookService.process(...).

        return HttpResponse(status=200)
    