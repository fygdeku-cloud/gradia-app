from __future__ import annotations

from django.contrib import messages
from django.db import transaction, IntegrityError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from ..forms import UserSignupForm
from ..models import StudentProfile, User
from ..mixins import RedirectAuthenticatedUserMixin, RedirectToNextOrReferrerMixin
from ..services import OtpEmailService, OtpRateLimitError, OtpService
from gradia.utils.enums import OtpPurpose

class RegisterView(
    RedirectAuthenticatedUserMixin,
    RedirectToNextOrReferrerMixin,
    FormView,
):
    template_name = "users/register.html"
    form_class = UserSignupForm

    def form_valid(self, form):
        try:
            with transaction.atomic():
                user = form.save()
                StudentProfile.objects.create(user=user)
                otp, token = OtpService.create(user=user, purpose=OtpPurpose.SIGNUP)
                OtpEmailService.send_otp(user=user, otp=otp, template="emails/users/email_verification.html")
        except IntegrityError:
            email = form.cleaned_data.get("email")
            if email and User.objects.filter(email__iexact=email).exists():
                messages.error(
                    self.request,
                    _("Un compte existe déjà avec cette adresse e-mail."),
                )
            else:
                messages.error(
                    self.request,
                    _("Une erreur est survenue lors de la création du compte."),
                )
            return self.form_invalid(form)
        except OtpRateLimitError as error:
            messages.warning(self.request, error)
            return self.form_invalid(form)
        self.request.session["pending_signup_token"] = token
        messages.success(self.request, _("Votre compte a été créé. Entrez le code reçu par e-mail pour l'activer."))
        return redirect(reverse("users:verify_email") + f"?token={token}")

    def form_invalid(self, form):
        messages.error(self.request, _("Veuillez corriger les informations d'inscription."))
        return super().form_invalid(form)
