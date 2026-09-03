from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView

from ..forms import EmailVerificationForm
from ..mixins import RedirectToNextOrReferrerMixin
from ..services import (
    OtpEmailService,
    OtpRateLimitError,
    OtpService,
    OtpVerificationError,
    OtpVerifyService,
)
from gradia.utils.enums import OtpPurpose


class EmailVerificationView(RedirectToNextOrReferrerMixin, FormView):
    """
    Vérification OTP pour les purposes signup et login.

    Adaptation de VerifyOtpView de la référence :
    - purpose/token lus depuis la query string ou le POST ;
    - le purpose password_reset est routé vers PasswordResetOtpView ;
    - après vérification, l'utilisateur est connecté puis redirigé
      vers `?next=` / `LOGIN_REDIRECT_URL`.
    """

    template_name = "users/verify_email.html"
    form_class = EmailVerificationForm

    def dispatch(self, request, *args, **kwargs):
        self.purpose = (
            request.GET.get("purpose") or request.POST.get("purpose", OtpPurpose.SIGNUP)
        )
        self.token = request.GET.get("token") or request.POST.get("token")

        # Le purpose password_reset possède sa propre présentation
        # (PasswordResetOtpView). On route ici plutôt que de dupliquer.
        if self.purpose == OtpPurpose.PASSWORD_RESET:
            url = reverse("users:password_reset_otp")
            if self.token:
                return redirect(f"{url}?token={self.token}")
            return redirect(url)

        if self.purpose not in {OtpPurpose.SIGNUP, OtpPurpose.LOGIN}:
            messages.error(request, _("Cette vérification n'est pas disponible."))
            return redirect("users:login")

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {"token": self.token}

    def form_valid(self, form):
        token = form.cleaned_data.get("token") or self.token
        code = form.cleaned_data.get("code")

        try:
            otp = OtpVerifyService.verify(token=token, code=code, purpose=self.purpose)
        except OtpVerificationError as error:
            messages.error(self.request, str(error))
            return self.form_invalid(form)

        messages.success(self.request, _("Votre compte est maintenant vérifié."))
        # Comme dans la référence VerifyOtpView, vérifier un OTP signup/login
        # connecte directement l'utilisateur (redirection next / profile).
        login(self.request, otp.user)
        if self.purpose == OtpPurpose.SIGNUP:
            return redirect("users:profile")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, _("Veuillez vérifier le code saisi."))
        return super().form_invalid(form)


class ResendVerificationView(RedirectToNextOrReferrerMixin, View):
    """
    Renvoi d'un nouveau code OTP (équivalent de ResendOtpView).
    Uniquement en POST ; le template email est choisi selon le purpose.
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        purpose = request.POST.get("purpose", OtpPurpose.SIGNUP)
        token = request.POST.get("token")

        try:
            with transaction.atomic():
                otp = OtpVerifyService._resolve_otp(token, purpose)
                new_otp, new_token = OtpService.create(otp.user, purpose)
                template = (
                    "emails/users/password_reset_otp.html"
                    if purpose == OtpPurpose.PASSWORD_RESET
                    else "emails/users/email_verification.html"
                )
                OtpEmailService.send_otp(otp.user, new_otp, template=template)
        except (OtpVerificationError, OtpRateLimitError, ValueError) as error:
            messages.error(request, error)
            return redirect(
                f"{reverse('users:verify_email')}?token={token}&purpose={purpose}"
            )

        messages.success(request, _("Un nouveau code vous a été envoyé."))
        return redirect(
            f"{reverse('users:verify_email')}?token={new_token}&purpose={purpose}"
        )
