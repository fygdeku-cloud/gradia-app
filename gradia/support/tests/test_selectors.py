from __future__ import annotations

import uuid

import pytest

from gradia.support.selectors import (
    get_manageable_tickets,
    get_ticket_detail,
    get_user_tickets,
)
from gradia.support.tests.factories import TicketFactory
from gradia.utils.enums import Priority, TicketStatus


@pytest.mark.django_db
class TestGetUserTickets:
    def test_returns_only_own_tickets_newest_first(self, student, other_user):
        mine_older = TicketFactory(student=student, title="Ancien")
        mine_newer = TicketFactory(student=student, title="Récent")
        TicketFactory(student=other_user, title="Autrui")

        result = list(get_user_tickets(student))

        assert [t.pk for t in result] == [mine_newer.pk, mine_older.pk]

    def test_returns_empty_for_user_without_tickets(self, student):
        assert list(get_user_tickets(student)) == []


@pytest.mark.django_db
class TestGetTicketDetail:
    def test_returns_own_ticket(self, student):
        ticket = TicketFactory(student=student)

        assert get_ticket_detail(ticket.pk, student) == ticket

    def test_returns_none_for_another_user_ticket(self, student, other_user):
        ticket = TicketFactory(student=other_user)

        assert get_ticket_detail(ticket.pk, student) is None

    def test_returns_none_for_missing_ticket(self, student):
        assert get_ticket_detail(uuid.uuid4(), student) is None


@pytest.mark.django_db
class TestGetManageableTickets:
    def test_returns_all_tickets_ordered(self, student, other_user):
        first = TicketFactory(student=student)
        second = TicketFactory(student=other_user)

        result = list(get_manageable_tickets())

        assert {t.pk for t in result} == {first.pk, second.pk}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", TicketStatus.CLOSED),
        ("priority", Priority.URGENT),
    ],
)
def test_factory_can_persist_status_and_priority(field, value, student):
    ticket = TicketFactory(student=student, **{field: value})

    ticket.refresh_from_db()
    assert getattr(ticket, field) == value
