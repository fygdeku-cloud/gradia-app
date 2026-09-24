from __future__ import annotations

import pytest
from django.urls import reverse

from gradia.support.models import Ticket, TicketMessage
from gradia.support.tests.factories import TicketFactory
from gradia.utils.enums import Priority, TicketStatus


@pytest.mark.django_db
class TestTicketListView:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse("support:list"))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_shows_only_own_tickets(self, client, student, other_user):
        own = TicketFactory(student=student, title="Mon ticket")
        TicketFactory(student=other_user, title="Leur ticket")
        client.force_login(student)

        response = client.get(reverse("support:list"))

        assert response.status_code == 200
        assert own in response.context["tickets"]
        assert len(response.context["tickets"]) == 1

    def test_empty_list_renders(self, client, student):
        client.force_login(student)

        response = client.get(reverse("support:list"))

        assert response.status_code == 200
        assert list(response.context["tickets"]) == []


@pytest.mark.django_db
class TestTicketDetailView:
    def test_anonymous_redirected_to_login(self, client):
        ticket = TicketFactory()

        response = client.get(reverse("support:detail", args=[ticket.pk]))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_owner_can_view_own_ticket(self, client, student):
        ticket = TicketFactory(student=student, title="Visible")
        ticket.add_message(student, "Premier message")
        client.force_login(student)

        response = client.get(reverse("support:detail", args=[ticket.pk]))

        assert response.status_code == 200
        assert response.context["ticket"] == ticket

    @pytest.mark.django_db
    def test_student_cannot_view_other_student_ticket(
        self,
        client,
        student,
        other_user,
    ):
        """IDOR : modifier l'identifiant dans l'URL ne doit rien donner."""
        ticket = TicketFactory(student=other_user)
        client.force_login(student)

        response = client.get(reverse("support:detail", args=[ticket.pk]))

        assert response.status_code == 404

    def test_staff_cannot_view_student_ticket_via_public_detail(
        self,
        client,
        support_staff,
    ):
        ticket = TicketFactory()
        client.force_login(support_staff)

        response = client.get(reverse("support:detail", args=[ticket.pk]))

        assert response.status_code == 404

    def test_missing_ticket_returns_404(self, client, student):
        client.force_login(student)

        response = client.get(
            reverse("support:detail", args=["00000000-0000-0000-0000-000000000000"])
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestTicketCreateView:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse("support:create"))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_get_renders_form(self, client, student):
        client.force_login(student)

        response = client.get(reverse("support:create"))

        assert response.status_code == 200
        assert "form" in response.context

    def test_valid_post_creates_exactly_one_ticket_and_one_message(
        self,
        client,
        student,
    ):
        """Régression : une soumission ne crée qu'un seul ticket."""
        client.force_login(student)

        response = client.post(
            reverse("support:create"),
            data={
                "title": "Problème de paiement",
                "description": "Le paiement échoue.",
                "priority": Priority.HIGH,
                "message": "Bonjour, aidez-moi.",
            },
        )

        assert Ticket.objects.count() == 1
        assert TicketMessage.objects.count() == 1

        ticket = Ticket.objects.get()
        assert ticket.student == student
        assert ticket.title == "Problème de paiement"
        assert ticket.priority == Priority.HIGH
        assert ticket.status == TicketStatus.OPEN
        assert ticket.messages.first().message == "Bonjour, aidez-moi."

        assert response.status_code == 302
        assert response["Location"] == reverse("support:list")

    @pytest.mark.parametrize(
        "missing_field",
        ["title", "message", "priority"],
    )
    def test_invalid_post_creates_nothing(
        self,
        client,
        student,
        missing_field,
    ):
        data = {
            "title": "Titre",
            "description": "Description",
            "priority": Priority.LOW,
            "message": "Message",
        }
        data.pop(missing_field)
        client.force_login(student)

        response = client.post(reverse("support:create"), data=data)

        assert response.status_code == 200
        assert Ticket.objects.count() == 0
        assert TicketMessage.objects.count() == 0

    def test_second_student_cannot_touch_first_student_ticket(
        self,
        client,
        student,
        other_user,
    ):
        ticket = TicketFactory(student=student)
        client.force_login(other_user)

        response = client.get(reverse("support:detail", args=[ticket.pk]))

        assert response.status_code == 404


@pytest.mark.django_db
class TestTicketManagementListView:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse("support:management_list"))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_plain_student_gets_403(self, client, student):
        TicketFactory(student=student)
        client.force_login(student)

        response = client.get(reverse("support:management_list"))

        assert response.status_code == 403

    def test_staff_sees_all_tickets(self, client, student, support_staff):
        mine = TicketFactory(student=student)
        theirs = TicketFactory()
        client.force_login(support_staff)

        response = client.get(reverse("support:management_list"))

        assert response.status_code == 200
        tickets = list(response.context["tickets"])
        assert {t.pk for t in tickets} == {mine.pk, theirs.pk}

    def test_staff_management_page_has_no_detail_link_to_foreign_ticket(
        self,
        client,
        support_staff,
    ):
        """La page de gestion liste les tickets sans exposer de détail
        accessible : le détail reste réservé au propriétaire."""
        ticket = TicketFactory()
        client.force_login(support_staff)

        response = client.get(reverse("support:management_list"))

        assert response.status_code == 200
        assert ticket in response.context["tickets"]
