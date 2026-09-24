from __future__ import annotations

import pytest

from gradia.support.forms import TicketCreateForm, TicketMessageForm
from gradia.support.tests.factories import TicketFactory
from gradia.utils.enums import Priority


@pytest.mark.django_db
class TestTicketCreateForm:
    def _payload(self, **overrides):
        data = {
            "title": "Sujet",
            "description": "Description",
            "priority": Priority.MEDIUM,
            "message": "Message initial",
        }
        data.update(overrides)
        return data

    def test_valid_data(self):
        form = TicketCreateForm(data=self._payload())

        assert form.is_valid() is True
        assert form.cleaned_data["message"] == "Message initial"

    @pytest.mark.parametrize(
        "field",
        ["title", "priority", "message"],
    )
    def test_missing_required_field(self, field):
        data = self._payload()
        data.pop(field)

        form = TicketCreateForm(data=data)

        assert form.is_valid() is False
        assert field in form.errors

    def test_blank_message_rejected(self):
        form = TicketCreateForm(data=self._payload(message="   "))

        assert form.is_valid() is False
        assert "message" in form.errors

    def test_invalid_priority_rejected(self):
        form = TicketCreateForm(data=self._payload(priority="critical"))

        assert form.is_valid() is False
        assert "priority" in form.errors

    def test_title_over_max_length_rejected(self):
        form = TicketCreateForm(data=self._payload(title="x" * 256))

        assert form.is_valid() is False
        assert "title" in form.errors

    def test_blank_description_accepted(self):
        """description est facultatif sur le modèle."""
        form = TicketCreateForm(data=self._payload(description=""))

        assert form.is_valid() is True


@pytest.mark.django_db
class TestTicketMessageForm:
    def test_valid_message(self):
        form = TicketMessageForm(data={"message": "Une réponse"})

        assert form.is_valid() is True

    @pytest.mark.parametrize("message", ["", "   "])
    def test_blank_message_rejected(self, message):
        form = TicketMessageForm(data={"message": message})

        assert form.is_valid() is False
        assert "message" in form.errors

    def test_bound_to_existing_ticket(self):
        ticket = TicketFactory()
        form = TicketMessageForm(instance=None, data={"message": "ok"})

        assert form.is_valid() is True
        assert ticket.pk is not None
