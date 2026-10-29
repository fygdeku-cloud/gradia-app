from django.conf import settings


def gradia_settings(request):
    """Expose Gradia settings in templates."""
    return {
        "ACCOUNT_ALLOW_REGISTRATION": getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True),
        # Devise par défaut (régionalisation) : toujours affichée depuis le
        # backend, jamais hardcodée dans les templates.
        "GRADIA_CURRENCY": getattr(settings, "DEFAULT_CURRENCY", ""),
        "GRADIA_CART_ENABLED": True,
    }
