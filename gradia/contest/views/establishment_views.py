from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from gradia.contest.selectors import (
    get_establishment_contests,
    get_establishment_detail,
    get_establishments,
)


class EstablishmentListView(ListView):
    """Catalogue public des établissements/organismes."""

    template_name = "contest/establishment_list.html"
    context_object_name = "establishments"

    def get_queryset(self):
        return get_establishments()


class EstablishmentDetailView(DetailView):
    """Détail public d'un établissement et de ses concours."""

    template_name = "contest/establishment_detail.html"
    context_object_name = "establishment"
    slug_url_kwarg = "slug"
    slug_field = "slug"

    def get_object(self, queryset=None):
        establishment = get_establishment_detail(
            self.kwargs.get("slug")
        )
        if establishment is None:
            raise Http404(
                _("Aucun établissement ne correspond à cette adresse.")
            )
        return establishment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contests"] = get_establishment_contests(self.object)
        return context