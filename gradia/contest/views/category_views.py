from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from gradia.contest.selectors import (
    get_categories,
    get_category_contests,
    get_category_detail,
)


class CategoryListView(ListView):
    """Catalogue public des catégories de concours."""

    template_name = "contest/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return get_categories()


class CategoryDetailView(DetailView):
    """Détail public d'une catégorie et de ses concours."""

    template_name = "contest/category_detail.html"
    context_object_name = "category"
    slug_url_kwarg = "slug"
    slug_field = "slug"

    def get_object(self, queryset=None):
        category = get_category_detail(
            self.kwargs.get("slug")
        )
        if category is None:
            raise Http404(
                _("Aucune catégorie de concours ne correspond à cette adresse.")
            )
        return category

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contests"] = get_category_contests(self.object)
        return context