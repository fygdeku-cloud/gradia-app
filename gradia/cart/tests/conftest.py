from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gradia.document.tests.factories import DocumentFactory
from gradia.utils.enums import CartStatus

if TYPE_CHECKING:
    from gradia.document.models import Document


@pytest.fixture
def paid_document() -> Document:
    return DocumentFactory(price=5000)


@pytest.fixture
def unpaid_document() -> Document:
    return DocumentFactory(price=0)


@pytest.fixture
def unpublished_document() -> Document:
    return DocumentFactory(is_published=False)