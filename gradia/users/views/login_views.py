from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from ..forms import UserLoginForm
from ..mixins import RedirectAuthenticatedUserMixin, RedirectToNextOrReferrerMixin
from ..services import OtpService, OtpEmailService, OtpRateLimitError
from gradia.utils.enums import OtpPurpose


class LoginView(RedirectAuthenticatedUserMixin, RedirectToNextOrReferrerMixin, FormView):
    """
    Connexion par email + mot de passe.

    - Utilisateur vérifié : authentification directe puis redirection
      `?next=` / `LOGIN_REDIRECT_URL` (adaptation de SigninView).
    - Utilisateur non vérifié : création d'un OTP LOGIN puis redirection
      vers la page de vérification OTP (`users:verify_email`).
    - Superutilisateur / staff : la vérification e-mail est contournée et le
      compte est automatiquement validé (`User.requires_email_verification`).
    """

    template_name = "users/login.html"
    form_class = UserLoginForm

    def get_success_url(self):
        """Redirige vers `?next=` uniquement s'il s'agit d'une URL interne sûre."""
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url and self.is_safe_url(next_url):
            return next_url
        return reverse(settings.LOGIN_REDIRECT_URL)

    def _verification_url(self, token):
        """
        URL Gradia de vérification OTP, équivalente au `users:verify_otp`
        de la référence (transport du purpose par query string).

        Le paramètre `next` est transmis à la page de vérification afin
        qu'après authentification l'utilisateur retrouve la page demandée.
        """
        url = f"{reverse('users:verify_email')}?purpose={OtpPurpose.LOGIN}&token={token}"
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url and self.is_safe_url(next_url):
            url += f"&next={quote(next_url)}"
        return url

    def form_valid(self, form):
        user = form.get_user()
        if user.requires_email_verification:
            try:
                otp, token = OtpService.create(user, OtpPurpose.LOGIN)
                self.request.session["pending_login_token"] = token
                OtpEmailService.send_otp(
                    user, otp, template="emails/users/email_verification.html"
                )
            except OtpRateLimitError as error:
                messages.warning(self.request, error)
                pending_token = self.request.session.get("pending_login_token", "")
                return redirect(self._verification_url(pending_token))

            messages.info(self.request, _("Un code de vérification vous a été envoyé."))
            return redirect(self._verification_url(token))

        # Superutilisateur / staff : l'étape de vérification e-mail est
        # contournée et le compte est validé automatiquement.
        user.auto_validate_email()

        login(self.request, user)
        messages.success(self.request, _("Connexion réussie."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Veuillez corriger les informations de connexion."))
        return super().form_invalid(form)
