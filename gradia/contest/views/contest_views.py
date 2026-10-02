from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from gradia.contest.permissions import StudentRequiredMixin
from gradia.contest.selectors import (
    get_contest_detail,
    get_contests,
    get_session_detail,
    get_session_documents,
)


class ContestListView(StudentRequiredMixin, ListView):
    """Catalogue des concours, réservé aux étudiants inscrits."""

    template_name = "contest/contest_list.html"
    context_object_name = "contests"

    def get_queryset(self):
        return get_contests()


class ContestDetailView(StudentRequiredMixin, DetailView):
    """Détail d'un concours et de ses sessions."""

    template_name = "contest/contest_detail.html"
    context_object_name = "contest"
    slug_url_kwarg = "slug"
    slug_field = "slug"

    def get_object(self, queryset=None):
        contest = get_contest_detail(
            self.kwargs.get("slug")
        )
        if contest is None:
            raise Http404(
                _("Aucun concours ne correspond à cette adresse.")
            )
        return contest


class SessionDetailView(StudentRequiredMixin, DetailView):
    """Détail d'une session de concours (année donnée)."""

    template_name = "contest/session_detail.html"
    context_object_name = "session"

    def get_object(self, queryset=None):
        session = get_session_detail(
            contest_slug=self.kwargs.get("contest_slug"),
            year=self.kwargs.get("year"),
        )
        if session is None:
            raise Http404(
                _("Aucune session de concours ne correspond à cette adresse.")
            )
        return session

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["documents"] = get_session_documents(
            self.object
        )
        return context