from django.conf import settings


def gradia_settings(request):
    """Expose Gradia settings in templates."""
    user = getattr(request, "user", None)
    # Les concours sont réservés aux étudiants inscrits : ce drapeau pilote
    # l'affichage des liens et des extraits de catalogue dans les templates.
    is_student = bool(
        user
        and user.is_authenticated
        and getattr(user, "is_student", False)
    )
    return {
        "ACCOUNT_ALLOW_REGISTRATION": getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True),
        # Devise par défaut (régionalisation) : toujours affichée depuis le
        # backend, jamais hardcodée dans les templates.
        "GRADIA_CURRENCY": getattr(settings, "DEFAULT_CURRENCY", ""),
        # Le module Cart/Order est désormais branché sur les routes réelles du
        # backend. Ce flag frontend active les parcours achat et paiement.
        "GRADIA_CART_ENABLED": True,
        # True uniquement pour un utilisateur authentifié ET inscrit comme
        # étudiant ; condition d'accès à toutes les vues `contest`.
        "is_student": is_student,
    }
