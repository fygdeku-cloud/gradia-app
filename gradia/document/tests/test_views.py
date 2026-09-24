from __future__ import annotations

import pytest
from django.urls import reverse

from gradia.document.tests.factories import DocumentFactory


@pytest.mark.django_db
class TestDocumentListView:
    def test_anonymous_can_list_published_documents(self, client, document, student):
        DocumentFactory(is_published=False)
        client.force_login(student)

        response = client.get(reverse("document:list"))

        assert response.status_code == 200
        assert document in response.context["documents"]

    def test_detail_context_exposes_has_paid(self, client, student, document):
        """Régession D2 : document_detail.html lit document.has_paid."""
        client.force_login(student)

        response = client.get(reverse("document:detail", kwargs={"pk": document.pk}))

        assert response.status_code == 200
        assert hasattr(response.context["document"], "has_paid") is True
        assert response.context["document"].has_paid is False

    def test_detail_for_anonymous_user_renders(self, client, document):
        response = client.get(reverse("document:detail", kwargs={"pk": document.pk}))

        assert response.status_code == 200
        assert response.context["document"].has_paid is False

    def test_unpublished_document_hidden_from_anonymous(self, client):
        doc = DocumentFactory(is_published=False)

        response = client.get(reverse("document:detail", kwargs={"pk": doc.pk}))

        assert response.status_code == 404


@pytest.mark.django_db
class TestDocumentManagementList:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse("document:management_list"))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_plain_student_gets_403(self, client, student, document):
        client.force_login(student)

        response = client.get(reverse("document:management_list"))

        assert response.status_code == 403


@pytest.mark.django_db
class TestDocumentAccessLogListView:
    def test_requires_staff(self, client, student, document, support_staff):
        client.force_login(student)
        assert client.get(reverse("document:access_logs")).status_code == 403

        client.force_login(support_staff)
        response = client.get(reverse("document:access_logs"))

        assert response.status_code == 200


@pytest.mark.django_db
class TestDocumentCreateUpdateDelete:
    def test_anonymous_redirected_to_login_on_create(self, client):
        response = client.get(reverse("document:create"))

        assert response.status_code == 302
        assert "/users/login/" in response["Location"]

    def test_create_form_renders_for_staff(self, client, support_staff, document):
        client.force_login(support_staff)

        response = client.get(reverse("document:create"))

        assert response.status_code == 200
        assert "form" in response.context

    def test_update_form_renders_for_staff(self, client, support_staff, document):
        client.force_login(support_staff)

        response = client.get(reverse("document:update", kwargs={"pk": document.pk}))

        assert response.status_code == 200

    def test_delete_confirm_renders_for_staff(self, client, support_staff, document):
        client.force_login(support_staff)

        response = client.get(reverse("document:delete", kwargs={"pk": document.pk}))

        assert response.status_code == 200