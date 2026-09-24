from __future__ import annotations

import pytest

from gradia.support.models import Ticket, TicketMessage
from gradia.utils.enums import Priority, TicketStatus


@pytest.mark.django_db
class TestTicketModel:
    def test_defaults_are_open_and_medium(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")

        assert ticket.status == TicketStatus.OPEN
        assert ticket.priority == Priority.MEDIUM
        assert ticket.is_open is True
        assert ticket.is_closed is False

    def test_in_progress_ticket_is_open(self, student):
        ticket = Ticket.objects.create(
            student=student,
            title="Titre",
            status=TicketStatus.IN_PROGRESS,
        )

        assert ticket.is_open is True
        assert ticket.is_closed is False

    @pytest.mark.parametrize(
        "status",
        [TicketStatus.RESOLVED, TicketStatus.CLOSED],
    )
    def test_resolved_and_closed_are_closed(self, student, status):
        ticket = Ticket.objects.create(
            student=student,
            title="Titre",
            status=status,
        )

        assert ticket.is_closed is True
        assert ticket.is_open is False

    def test_close_sets_status_and_reopen_reverts(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")

        ticket.close()
        assert ticket.status == TicketStatus.CLOSED

        ticket.reopen()
        assert ticket.status == TicketStatus.OPEN

    def test_close_on_closed_ticket_is_noop(self, student):
        ticket = Ticket.objects.create(
            student=student,
            title="Titre",
            status=TicketStatus.CLOSED,
        )

        ticket.close()
        ticket.refresh_from_db()
        assert ticket.status == TicketStatus.CLOSED

    def test_reopen_on_open_ticket_is_noop(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")

        ticket.reopen()
        ticket.refresh_from_db()
        assert ticket.status == TicketStatus.OPEN

    @pytest.mark.parametrize(
        "priority",
        [
            Priority.LOW,
            Priority.MEDIUM,
            Priority.HIGH,
            Priority.URGENT,
        ],
    )
    def test_set_priority_accepts_valid_values(self, student, priority):
        ticket = Ticket.objects.create(student=student, title="Titre")
        ticket.set_priority(priority)

        ticket.refresh_from_db()
        assert ticket.priority == priority

    def test_set_priority_rejects_unknown_value(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")

        with pytest.raises(ValueError):
            ticket.set_priority("critical")

    def test_set_priority_same_value_does_not_save(self, student):
        ticket = Ticket.objects.create(
            student=student,
            title="Titre",
            priority=Priority.MEDIUM,
        )
        original_updated_at = ticket.updated_at

        ticket.set_priority(Priority.MEDIUM)

        assert ticket.updated_at == original_updated_at

    def test_add_message_creates_message_and_strips(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")

        message = ticket.add_message(student, "  Bonjour  ")

        assert message.message == "Bonjour"
        assert message.sender == student
        assert message.ticket == ticket

    @pytest.mark.parametrize("message", ["", "   ", None])
    def test_add_message_rejects_blank_message(self, student, message):
        ticket = Ticket.objects.create(student=student, title="Titre")

        with pytest.raises(ValueError):
            ticket.add_message(student, message)

        assert ticket.messages.count() == 0

    def test_add_message_on_closed_ticket_rejected(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")
        ticket.close()

        with pytest.raises(ValueError):
            ticket.add_message(student, "Encore moi")

        assert ticket.messages.count() == 0

    def test_get_messages_are_ordered_and_select_related(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")
        first = ticket.add_message(student, "Premier")
        second = ticket.add_message(student, "Second")

        messages = list(ticket.get_messages())

        assert [m.pk for m in messages] == [first.pk, second.pk]

    def test_get_last_message_returns_most_recent(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")
        ticket.add_message(student, "Premier")
        last = ticket.add_message(student, "Dernier")

        assert ticket.get_last_message().pk == last.pk

    def test_get_last_message_without_messages_is_none(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")

        assert ticket.get_last_message() is None

    def test_ticket_str_contains_student_name(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")

        assert student.name in str(ticket)

    def test_messages_are_cascaded_on_ticket_delete(self, student):
        ticket = Ticket.objects.create(student=student, title="Titre")
        ticket.add_message(student, "Au revoir")
        message_pk = ticket.messages.first().pk

        ticket.delete()

        assert not TicketMessage.objects.filter(pk=message_pk).exists()
