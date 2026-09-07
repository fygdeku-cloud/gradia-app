from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView
from gradia.support.selectors import get_manageable_tickets

class TicketManagementListView(UserPassesTestMixin, ListView):
    template_name = "support/management/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return get_manageable_tickets()
