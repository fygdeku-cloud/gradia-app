import pytest
from gradia.contest.models import (
    Contest,
    ContestSession,
    Establishment,
)
from gradia.contest.selectors import (
    get_contest_detail,
    get_contests,
    get_establishment_contests,
    get_establishment_detail,
    get_establishments,
    get_session_detail,
    get_session_documents,
)
from gradia.document.tests.factories import (
    ContestFactory,
    ContestSessionFactory,
    DocumentFactory,
    EstablishmentFactory,
)


@pytest.mark.django_db
class TestContestSelectors:
    def test_get_contests(self):
        c1 = ContestFactory(title="Concours Alpha")
        c2 = ContestFactory(title="Concours Beta")
        results = list(get_contests())
        assert len(results) == 2
        assert results[0] == c1
        assert results[1] == c2

    def test_get_contest_detail(self):
        c1 = ContestFactory(title="ENSP Concours")
        assert get_contest_detail(c1.slug) == c1
        assert get_contest_detail("nonexistent-slug") is None

    def test_get_establishments_and_detail(self):
        est = EstablishmentFactory(title="Université de Yaoundé")
        ContestFactory(establishment=est)
        establishments = list(get_establishments())
        assert len(establishments) == 1
        assert establishments[0].contest_count == 1
        assert get_establishment_detail(est.slug) == est
        assert get_establishment_detail("nonexistent") is None

    def test_get_establishment_contests(self):
        est = EstablishmentFactory()
        c1 = ContestFactory(establishment=est, title="C1")
        assert list(get_establishment_contests(est)) == [c1]

    def test_get_session_detail(self):
        contest = ContestFactory(title="Session Contest")
        session = ContestSessionFactory(contest=contest, year=2023)
        assert get_session_detail(contest.slug, 2023) == session
        assert get_session_detail(contest.slug, 2099) is None
        assert get_session_detail("invalid-slug", 2023) is None

    def test_get_session_documents(self):
        session = ContestSessionFactory()
        doc1 = DocumentFactory(contest_session=session)
        doc2 = DocumentFactory(contest_session=session)
        docs = list(get_session_documents(session))
        assert len(docs) == 2
        assert doc1 in docs and doc2 in docs
