from __future__ import annotations

import factory

from gradia.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    """Factory pour la création d'un utilisateur Gradia."""

    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    name = factory.Faker("name")
    password = factory.PostGenerationMethodCall("set_password", "Passw0rd!2024")

    is_active = True
    is_student = True
    email_verified = True