from __future__ import annotations

import pytest
from django.urls import reverse

from gradia.document.tests.factories import DocumentFactory


@pytest.mark.django_db
class TestDocumentModel:
    def test_str_returns_title(self, document):
        assert str(document) == document.title

    def test_absolute_url_points_to_public_detail(self, document):
        assert document.get_absolute_url() == reverse(
            "document:detail",
            kwargs={"pk": document.pk},
        )

    def test_has_correction_true_when_file_set(self, document):
        assert document.has_correction() is True

    def test_has_correction_false_when_empty(self):
        doc = DocumentFactory(correction_file="")

        assert doc.has_correction() is False


@pytest.mark.django_db
class TestDocumentAccessLogModel:
    def test_str_contains_title(self, document, student):
        from gradia.document.models import DocumentAccessLog
        from gradia.utils.enums import ACTION_DOWNLOAD_SUBJECT

        log = DocumentAccessLog.objects.create(
            user=student,
            document=document,
            action=ACTION_DOWNLOAD_SUBJECT,
        )

        assert document.title in str(log)