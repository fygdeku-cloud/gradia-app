from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from gradia.support.selectors import get_user_tickets

class TicketListView(LoginRequiredMixin, ListView):
    template_name = "support/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 20

    def get_queryset(self):
        return get_user_tickets(self.request.user)
