from __future__ import annotations

import factory

from gradia.support.models import Ticket, TicketMessage
from gradia.utils.enums import Priority, TicketStatus


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ticket

    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("paragraph")
