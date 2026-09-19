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

        context = {
            "user": request.user,
            "profile": profile,
            "form": form,
        }

        if getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False) or getattr(request.user, "is_admin", False):
            from django.contrib.auth import get_user_model
            from gradia.document.models import Document
            from gradia.contest.models import Contest
            User = get_user_model()
            context["student_count"] = User.objects.filter(is_student=True).count()
            context["published_docs_count"] = Document.objects.filter(is_published=True).count()
            context["active_contests_count"] = Contest.objects.count()

        if getattr(request.user, "is_student", False):
            from gradia.document.models import DocumentAccessLog
            logs = DocumentAccessLog.objects.filter(user=request.user).select_related('document').order_by('-accessed_at')[:5]
            recent_documents = [
                {
                    "title": log.document.title,
                    "accessed_at": log.accessed_at
                } for log in logs
            ]
            context["recent_documents"] = recent_documents

        return render(
            request,
            self.template_name,
            context,
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
