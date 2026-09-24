from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gradia.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from gradia.users.models import User


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    return UserFactory.create()


@pytest.fixture
def student(db) -> User:
    return UserFactory.create(is_student=True)


@pytest.fixture
def other_user(db) -> User:
    return UserFactory.create(is_student=True)


@pytest.fixture
def support_staff(db) -> User:
    return UserFactory.create(is_staff=True, is_student=False)