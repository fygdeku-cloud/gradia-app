from django.views.generic import TemplateView

from gradia.contest.models import Contest
from gradia.contest.models import ContestSession


class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["home_contests"] = list(
            Contest.objects.select_related(
                "establishment",
                "category",
            )
            .prefetch_related("sessions")
            .order_by("-created_at")[:6],
        )
        context["home_sessions"] = list(
            ContestSession.objects.select_related(
                "contest__establishment",
                "contest__category",
            ).order_by("-year")[:6],
        )
        return context
