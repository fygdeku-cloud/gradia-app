from __future__ import annotations

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
    """

    template_name = "users/login.html"
    form_class = UserLoginForm

    def get_success_url(self):
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return next_url or reverse(settings.LOGIN_REDIRECT_URL)

    def _verification_url(self, token):
        """
        URL Gradia de vérification OTP, équivalente au `users:verify_otp`
        de la référence (transport du purpose par query string).
        """
        return f"{reverse('users:verify_email')}?purpose={OtpPurpose.LOGIN}&token={token}"

    def form_valid(self, form):
        user = form.get_user()
        if not user.email_verified:
            try:
                otp, token = OtpService.create(user, OtpPurpose.LOGIN)
                OtpEmailService.send_otp(
                    user, otp, template="emails/users/email_verification.html"
                )
            except OtpRateLimitError as error:
                messages.warning(self.request, error)
                pending_token = self.request.session.get("pending_login_token", "")
                return redirect(self._verification_url(pending_token))

            self.request.session["pending_login_token"] = token
            messages.info(self.request, _("Un code de vérification vous a été envoyé."))
            return redirect(self._verification_url(token))

        login(self.request, user)
        messages.success(self.request, _("Connexion réussie."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Veuillez corriger les informations de connexion."))
        return super().form_invalid(form)
