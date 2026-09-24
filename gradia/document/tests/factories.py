from __future__ import annotations

import factory

from gradia.contest.models import (
    Contest,
    ContestCategory,
    ContestSession,
    Establishment,
)
from gradia.document.models import Document


class EstablishmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Establishment

    title = factory.Sequence(lambda n: f"Établissement {n}")
    name = factory.Sequence(lambda n: f"Etablissement {n}")
    location = factory.Faker("city")


class ContestCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContestCategory

    title = factory.Sequence(lambda n: f"Catégorie {n}")


class ContestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contest

    title = factory.Sequence(lambda n: f"Concours {n}")
    establishment = factory.SubFactory(EstablishmentFactory)
    category = factory.SubFactory(ContestCategoryFactory)


class ContestSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContestSession

    contest = factory.SubFactory(ContestFactory)
    title = factory.Sequence(lambda n: f"Session {n}")
    year = factory.Faker("year")


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document

    title = factory.Sequence(lambda n: f"Document {n}")
    description = factory.Faker("paragraph")
    context = factory.Faker("word")
    contest_session = factory.SubFactory(ContestSessionFactory)
    subject_file = factory.django.FileField(
        filename="sujet.pdf",
        data=b"%PDF-1.4\n%dummy subject",
    )
    correction_file = factory.django.FileField(
        filename="correction.pdf",
        data=b"%PDF-1.4\n%dummy correction",
    )
    price = factory.Sequence(lambda n: 1000 + n)
    is_published = True