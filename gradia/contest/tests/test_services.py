import datetime
import pytest
from django.core.exceptions import ValidationError
from gradia.contest.models import (
    Contest,
    ContestCategory,
    ContestSession,
    Establishment,
)
from gradia.contest.services import (
    CategoryService,
    ContestService,
    EstablishmentService,
    SessionService,
)
from gradia.document.tests.factories import (
    ContestCategoryFactory,
    ContestFactory,
    ContestSessionFactory,
    EstablishmentFactory,
)


@pytest.mark.django_db
class TestContestServices:
    def test_establishment_service_create_and_update(self):
        est = EstablishmentService.create(
            title="Polytech",
            description="Ecole d'ingénieur",
            location="Paris",
        )
        assert est.pk is not None
        assert est.title == "Polytech"
        assert est.slug is not None

        updated = EstablishmentService.update(
            est,
            title="Polytech Paris",
            location="Saclay",
        )
        assert updated.title == "Polytech Paris"
        assert updated.location == "Saclay"

    def test_establishment_service_invalid_title(self):
        with pytest.raises(ValidationError):
            EstablishmentService.create(title="   ")

    def test_category_service_create_and_update(self):
        cat = CategoryService.create(
            title="Médecine",
            description="Concours médicaux",
        )
        assert cat.pk is not None
        assert cat.title == "Médecine"

        updated = CategoryService.update(cat, title="Santé & Médecine")
        assert updated.title == "Santé & Médecine"

    def test_category_service_invalid_title(self):
        with pytest.raises(ValidationError):
            CategoryService.create(title="")

    def test_contest_service_create_and_update(self):
        est = EstablishmentFactory()
        cat = ContestCategoryFactory()
        contest = ContestService.create(
            title="Concours National",
            establishment=est,
            category=cat,
            description="Description concours",
            requirements="Bac+2 requis",
        )
        assert contest.pk is not None
        assert contest.title == "Concours National"

        updated = ContestService.update(contest, title="Concours National 2024", requirements="Bac+3 requis")
        assert updated.title == "Concours National 2024"
        assert updated.requirements == "Bac+3 requis"

    def test_contest_service_invalid_title(self):
        est = EstablishmentFactory()
        cat = ContestCategoryFactory()
        with pytest.raises(ValidationError):
            ContestService.create(title="  ", establishment=est, category=cat)

    def test_session_service_create_and_update(self):
        contest = ContestFactory()
        session = SessionService.create(
            contest=contest,
            year=2024,
            title="Session Principale 2024",
            registration_start_date=datetime.date(2024, 1, 1),
            registration_end_date=datetime.date(2024, 3, 1),
            exam_date=datetime.date(2024, 4, 1),
        )
        assert session.pk is not None
        assert session.year == 2024

        updated = SessionService.update(session, title="Session Modifiée 2024", year=2024)
        assert updated.title == "Session Modifiée 2024"

    def test_session_service_invalid_title(self):
        contest = ContestFactory()
        with pytest.raises(ValidationError):
            SessionService.create(contest=contest, year=2024, title="  ")
