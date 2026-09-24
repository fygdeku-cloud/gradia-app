from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gradia.document.tests.factories import DocumentFactory

if TYPE_CHECKING:
    from gradia.document.models import Document


@pytest.fixture
def document() -> Document:
    return DocumentFactory()


@pytest.fixture
def unpublished_document() -> Document:
    return DocumentFactory(is_published=False)


@pytest.fixture
def free_document() -> Document:
    return DocumentFactory(price=0)