from django.db.models import QuerySet
from .models import Ticket

def get_user_tickets(user) -> QuerySet:
    return Ticket.objects.filter(student=user).order_by("-created_at")

def get_ticket_detail(ticket_id, user) -> Ticket | None:
    return Ticket.objects.filter(pk=ticket_id, student=user).first()

def get_manageable_tickets() -> QuerySet:
    return Ticket.objects.all().order_by("-created_at")
