from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from gradia.support.selectors import get_ticket_detail

class TicketDetailView(LoginRequiredMixin, DetailView):
    template_name = "support/ticket_detail.html"
    context_object_name = "ticket"
    pk_url_kwarg = "ticket_id"

    def get_object(self, queryset=None):
        ticket = get_ticket_detail(
            self.kwargs.get("ticket_id"),
            self.request.user,
        )
        if ticket is None:
            raise Http404(
                _("Aucun ticket ne correspond à cette adresse.")
            )
        return ticket
