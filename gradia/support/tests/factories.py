from __future__ import annotations

import factory

from gradia.support.models import Ticket
from gradia.users.tests.factories import UserFactory


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ticket

    student = factory.SubFactory(UserFactory)
    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("paragraph")