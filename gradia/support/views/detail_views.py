from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from gradia.support.selectors import get_ticket_detail

class TicketDetailView(LoginRequiredMixin, DetailView):
    template_name = "support/ticket_detail.html"
    context_object_name = "ticket"
    pk_url_kwarg = "ticket_id"

    def get_object(self, queryset=None):
        return get_object_or_404(
            get_ticket_detail(self.kwargs.get("ticket_id"), self.request.user)
        )
