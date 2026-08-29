from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from ..forms import StudentProfileForm
from ..models import StudentProfile


class ProfileView(LoginRequiredMixin, View):
    """Consultation et modification du profil utilisateur."""

    template_name = "users/profile.html"
    profile_form_class = StudentProfileForm

    def get(self, request):
        profile = self._get_student_profile(
            request.user
        )

        form = self.profile_form_class(
            instance=profile,
        )

        return render(
            request,
            self.template_name,
            {
                "user": request.user,
                "profile": profile,
                "form": form,
            },
        )

    def post(self, request):
        profile = self._get_student_profile(
            request.user
        )

        form = self.profile_form_class(
            request.POST,
            instance=profile,
        )

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "user": request.user,
                    "profile": profile,
                    "form": form,
                },
                status=400,
            )

        form.save()

        messages.success(
            request,
            _("Your profile has been updated successfully."),
        )

        return redirect(
            "users:profile"
        )

    @staticmethod
    def _get_student_profile(user):
        profile, _ = (
            StudentProfile.objects.get_or_create(
                user=user,
            )
        )

        return profile
