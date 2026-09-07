from django.db import transaction
from .models import Ticket

class SupportService:
    @staticmethod
    @transaction.atomic
    def create_ticket(student, form_data, initial_message) -> Ticket:
        ticket = Ticket.objects.create(
            student=student,
            title=form_data["title"],
            description=form_data.get("description", ""),
            priority=form_data.get("priority", "medium"),
        )
        ticket.add_message(sender=student, message=initial_message)
        return ticket

    @staticmethod
    @transaction.atomic
    def add_message(ticket, sender, message) -> None:
        ticket.add_message(sender=sender, message=message)

    @staticmethod
    @transaction.atomic
    def change_status(ticket, status) -> None:
        ticket.status = status
        ticket.save(update_fields=["status"])
