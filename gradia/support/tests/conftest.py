from __future__ import annotations

import pytest

from gradia.users.tests.factories import UserFactory


@pytest.fixture
def student() -> User:
    return UserFactory.create(is_student=True)


@pytest.fixture
def support_staff() -> User:
    return UserFactory.create(is_staff=True)
