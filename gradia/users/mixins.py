from django.shortcuts import redirect
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import View

class RedirectAuthenticatedUserMixin:
    """
    Mixin pour rediriger un utilisateur déjà authentifié loin des pages
    telles que le Login ou le Register.
    """
    redirect_url = getattr(settings, "LOGIN_REDIRECT_URL", "/")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.redirect_url)
        return super().dispatch(request, *args, **kwargs)

class RedirectToNextOrReferrerMixin:
    """
    Mixin qui redirige vers :
    1. Le paramètre `?next=` (si présent et sûr),
    2. Sinon le référent (`HTTP_REFERER`) s'il est interne,
    3. Sinon une URL fallback (par défaut la home).
    """

    fallback_url = getattr(settings, "LOGIN_REDIRECT_URL", "/")

    def is_safe_url(self, url):
        """Vérifie que l'URL est interne (pas d'open redirect)."""
        return url_has_allowed_host_and_scheme(
            url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        )

    def get_redirect_url(self):
        """
        Retourne l'URL de redirection prioritaire.
        Surchargez cette méthode dans les vues qui ont un `next` spécifique.
        """
        next_url = self.request.GET.get("next")
        if next_url and self.is_safe_url(next_url):
            return next_url

        referrer = self.request.META.get("HTTP_REFERER")
        if referrer and self.is_safe_url(referrer):
            return referrer

        return reverse(self.fallback_url)

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    # Méthode utilisée par FormView après un formulaire valide
    def get_success_url(self):
        return self.get_redirect_url()
