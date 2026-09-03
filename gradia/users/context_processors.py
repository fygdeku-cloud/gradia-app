from django.conf import settings


def gradia_settings(request):
    """Expose Gradia settings in templates."""
    return {
        "ACCOUNT_ALLOW_REGISTRATION": getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True),
    }
