from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView
from gradia.support.forms import TicketCreateForm
from gradia.support.services import SupportService

class TicketCreateView(LoginRequiredMixin, CreateView):
    form_class = TicketCreateForm
    template_name = "support/ticket_form.html"
    success_url = reverse_lazy("support:list")

    def form_valid(self, form):
        SupportService.create_ticket(
            student=self.request.user,
            form_data=form.cleaned_data,
            initial_message=form.cleaned_data["message"],
        )
        return super().form_valid(form)
