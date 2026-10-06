import pytest
from django.urls import reverse
from gradia.document.tests.factories import (
    ContestFactory,
    ContestSessionFactory,
    DocumentFactory,
    EstablishmentFactory,
)


@pytest.fixture
def student_client(client, student):
    """Client authentifié en tant qu'étudiant (seul profil autorisé)."""
    client.force_login(student)
    return client


@pytest.mark.django_db
class TestContestViews:
    def test_contest_list_view(self, student_client):
        c1 = ContestFactory(title="Concours A")
        c2 = ContestFactory(title="Concours B")
        url = reverse("contest:list")
        response = student_client.get(url)
        assert response.status_code == 200
        assert c1.title in response.content.decode()
        assert c2.title in response.content.decode()

    def test_contest_detail_view(self, student_client):
        contest = ContestFactory(title="Grand Concours")
        url = reverse("contest:detail", kwargs={"slug": contest.slug})
        response = student_client.get(url)
        assert response.status_code == 200
        assert "Grand Concours" in response.content.decode()

    def test_contest_detail_view_404(self, student_client):
        url = reverse("contest:detail", kwargs={"slug": "unknown-slug"})
        response = student_client.get(url)
        assert response.status_code == 404

    def test_establishment_list_view(self, student_client):
        est = EstablishmentFactory(title="ENSP Yaoundé")
        url = reverse("contest:establishment_list")
        response = student_client.get(url)
        assert response.status_code == 200
        assert "ENSP Yaoundé" in response.content.decode()

    def test_establishment_detail_view(self, student_client):
        est = EstablishmentFactory(title="Université de Douala")
        contest = ContestFactory(establishment=est, title="Concours Douala")
        url = reverse("contest:establishment_detail", kwargs={"slug": est.slug})
        response = student_client.get(url)
        assert response.status_code == 200
        assert "Université de Douala" in response.content.decode()
        assert "Concours Douala" in response.content.decode()

    def test_establishment_detail_view_404(self, student_client):
        url = reverse("contest:establishment_detail", kwargs={"slug": "inexistant"})
        response = student_client.get(url)
        assert response.status_code == 404

    def test_session_detail_view(self, student_client):
        contest = ContestFactory(title="Concours Médecine")
        session = ContestSessionFactory(contest=contest, year=2024, title="Session 2024")
        doc = DocumentFactory(contest_session=session, title="Epreuve de Chimie")
        url = reverse("contest:session_detail", kwargs={"contest_slug": contest.slug, "year": 2024})
        response = student_client.get(url)
        assert response.status_code == 200
        assert "Session 2024" in response.content.decode()
        assert "Epreuve de Chimie" in response.content.decode()

    def test_session_detail_view_404(self, student_client):
        contest = ContestFactory()
        url = reverse("contest:session_detail", kwargs={"contest_slug": contest.slug, "year": 2099})
        response = student_client.get(url)
        assert response.status_code == 404
