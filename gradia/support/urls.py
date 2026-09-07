from django.urls import path
from gradia.support.views import (
    TicketCreateView,
    TicketDetailView,
    TicketListView,
    TicketManagementListView,
)

app_name = "support"

urlpatterns = [
    path("tickets/", TicketListView.as_view(), name="list"),
    path("tickets/create/", TicketCreateView.as_view(), name="create"),
    path("tickets/<uuid:ticket_id>/", TicketDetailView.as_view(), name="detail"),
    path("management/", TicketManagementListView.as_view(), name="management_list"),
]
