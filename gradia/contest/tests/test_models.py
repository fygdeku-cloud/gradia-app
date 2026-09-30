import datetime
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from gradia.contest.models import (
    Contest,
    ContestCategory,
    ContestSession,
    Establishment,
)
from gradia.document.tests.factories import (
    ContestCategoryFactory,
    ContestFactory,
    ContestSessionFactory,
    DocumentFactory,
    EstablishmentFactory,
)


@pytest.mark.django_db
class TestEstablishmentModel:
    def test_establishment_str_and_slug(self):
        est = EstablishmentFactory(title="Ecole Polytechnique")
        assert str(est) == "Ecole Polytechnique"
        assert est.slug is not None
        assert "ecole-polytechnique" in est.slug
        assert est.get_absolute_url() == f"/contest/etablissement/{est.slug}/"

    def test_establishment_get_contests(self):
        est = EstablishmentFactory()
        contest = ContestFactory(establishment=est)
        assert list(est.get_contests()) == [contest]


@pytest.mark.django_db
class TestContestCategoryModel:
    def test_category_str_and_slug(self):
        cat = ContestCategoryFactory(title="Ingénierie")
        assert str(cat) == "Ingénierie"
        assert cat.slug is not None
        assert "ingenierie" in cat.slug
        assert cat.get_absolute_url() == f"/contest/categorie/{cat.slug}/"

    def test_category_get_contests(self):
        cat = ContestCategoryFactory()
        contest = ContestFactory(category=cat)
        assert list(cat.get_contests()) == [contest]


@pytest.mark.django_db
class TestContestModel:
    def test_contest_str_and_slug(self):
        est = EstablishmentFactory(title="ENSP")
        cat = ContestCategoryFactory(title="Ingénieur")
        contest = ContestFactory(title="Concours Entrée 2024", establishment=est, category=cat)
        assert str(contest) == "Concours Entrée 2024"
        assert contest.slug is not None
        assert contest.get_absolute_url() == f"/contest/{contest.slug}/"

    def test_contest_unique_per_establishment(self):
        est = EstablishmentFactory()
        cat = ContestCategoryFactory()
        ContestFactory(title="Concours A", establishment=est, category=cat)
        with pytest.raises(IntegrityError):
            Contest.objects.create(title="Concours A", establishment=est, category=cat)

    def test_contest_get_sessions(self):
        contest = ContestFactory()
        session = ContestSessionFactory(contest=contest)
        assert list(contest.get_contest_sessions()) == [session]


@pytest.mark.django_db
class TestContestSessionModel:
    def test_session_str_and_urls(self):
        contest = ContestFactory(title="Mines Paris")
        session = ContestSessionFactory(contest=contest, year=2024, title="Session 2024")
        assert "Mines Paris" in str(session)
        assert "Session 2024" in str(session)
        assert session.get_absolute_url() == f"/contest/{contest.slug}/2024/"

    def test_session_unique_year_per_contest(self):
        contest = ContestFactory()
        ContestSessionFactory(contest=contest, year=2025)
        with pytest.raises(IntegrityError):
            ContestSession.objects.create(contest=contest, year=2025, title="Session 2025 Bis")

    def test_session_get_documents(self):
        session = ContestSessionFactory()
        doc = DocumentFactory(contest_session=session)
        assert list(session.get_documents()) == [doc]
