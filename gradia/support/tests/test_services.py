from __future__ import annotations

import pytest

from gradia.support.services import SupportService
from gradia.support.tests.factories import TicketFactory
from gradia.utils.enums import Priority, TicketStatus


@pytest.mark.django_db
class TestCreateTicket:
    def test_creates_ticket_with_initial_message(self, student):
        ticket = SupportService.create_ticket(
            student=student,
            form_data={
                "title": "Problème de connexion",
                "description": "Je ne peux pas me connecter.",
                "priority": Priority.HIGH,
            },
            initial_message="Bonjour, une aide s'il vous plaît.",
        )

        assert ticket.student == student
        assert ticket.title == "Problème de connexion"
        assert ticket.description == "Je ne peux pas me connecter."
        assert ticket.priority == Priority.HIGH
        assert ticket.status == TicketStatus.OPEN
        assert ticket.messages.count() == 1

        message = ticket.messages.first()
        assert message.sender == student
        assert message.message == "Bonjour, une aide s'il vous plaît."

    def test_defaults_when_optional_data_missing(self, student):
        ticket = SupportService.create_ticket(
            student=student,
            form_data={"title": "Titre seul"},
            initial_message="Message",
        )

        assert ticket.description == ""
        assert ticket.priority == Priority.MEDIUM

    def test_initial_message_is_stripped(self, student):
        ticket = SupportService.create_ticket(
            student=student,
            form_data={"title": "Titre"},
            initial_message="  Espaces  ",
        )

        assert ticket.messages.first().message == "Espaces"

    @pytest.mark.parametrize("initial_message", ["", "   "])
    def test_empty_initial_message_creates_no_ticket(
        self,
        student,
        initial_message,
    ):
        """Le service est atomique : un message invalide annule le ticket."""
        with pytest.raises(ValueError):
            SupportService.create_ticket(
                student=student,
                form_data={"title": "Titre"},
                initial_message=initial_message,
            )

        assert not student.tickets.exists()


@pytest.mark.django_db
class TestAddMessage:
    def test_add_message_to_open_ticket(self, student):
        ticket = TicketFactory(student=student)

        SupportService.add_message(ticket, student, "Réponse du support")

        assert ticket.messages.count() == 1
        assert ticket.messages.first().message == "Réponse du support"

    def test_add_message_to_closed_ticket_raises(self, student):
        ticket = TicketFactory(student=student)
        ticket.close()

        with pytest.raises(ValueError):
            SupportService.add_message(ticket, student, "Encore")

        assert ticket.messages.count() == 0


@pytest.mark.django_db
class TestChangeStatus:
    @pytest.mark.parametrize(
        "status",
        [
            TicketStatus.IN_PROGRESS,
            TicketStatus.RESOLVED,
            TicketStatus.CLOSED,
        ],
    )
    def test_change_status_persists_value(self, student, status):
        ticket = TicketFactory(student=student)

        SupportService.change_status(ticket, status)

        ticket.refresh_from_db()
        assert ticket.status == status
