"""
Tests de la règle d'accès aux concours.

Règle métier : les vues `contest` sont réservées aux étudiants inscrits.
- visiteur anonyme        -> redirection vers `users:login` (avec `?next=`)
- connecté non étudiant  -> redirection vers `users:profile` (avec `?next=`)
- étudiant                -> accès autorisé (200)
"""

import pytest
from django.urls import reverse

from gradia.document.tests.factories import ContestFactory
from gradia.users.tests.factories import UserFactory


def contest_urls():
    """Toutes les URLs du namespace `contest` qui doivent être protégées."""
    return [
        reverse("contest:list"),
        reverse("contest:category_list"),
        reverse("contest:category_detail", kwargs={"slug": "slug-test"}),
        reverse("contest:establishment_list"),
        reverse("contest:establishment_detail", kwargs={"slug": "slug-test"}),
        reverse("contest:detail", kwargs={"slug": "slug-test"}),
        reverse(
            "contest:session_detail",
            kwargs={"contest_slug": "slug-test", "year": 2024},
        ),
    ]


@pytest.fixture
def non_student(db):
    """Utilisateur authentifié mais NON étudiant."""
    return UserFactory.create(is_student=False)


@pytest.mark.django_db
class TestContestAccessAnonymous:
    """Un visiteur non authentifié ne doit jamais consulter un concours."""

    @pytest.mark.parametrize("url", contest_urls())
    def test_anonymous_is_redirected_to_login(self, client, url):
        ContestFactory(slug="slug-test")
        response = client.get(url)

        assert response.status_code == 302
        assert response["Location"].startswith(reverse("users:login"))

    @pytest.mark.parametrize("url", contest_urls())
    def test_anonymous_receives_no_contest_content(self, client, url):
        """Aucune donnée de concours ne doit fuiter dans la réponse."""
        ContestFactory(title="Concours Secret", slug="slug-test")
        response = client.get(url, follow=True)

        assert "Concours Secret" not in response.content.decode()

    def test_next_parameter_is_preserved(self, client):
        """L'URL demandée est conservée pour revenir après connexion."""
        ContestFactory(slug="slug-test")
        url = reverse("contest:detail", kwargs={"slug": "slug-test"})
        response = client.get(url)

        assert response.status_code == 302
        assert f"next={url}" in response["Location"]


@pytest.mark.django_db
class TestContestAccessNonStudent:
    """Un utilisateur connecté non étudiant est renvoyé vers son profil."""

    @pytest.mark.parametrize("url", contest_urls())
    def test_non_student_is_redirected_to_profile(self, client, non_student, url):
        ContestFactory(slug="slug-test")
        client.force_login(non_student)
        response = client.get(url)

        assert response.status_code == 302
        assert response["Location"].startswith(reverse("users:profile"))

    @pytest.mark.parametrize("url", contest_urls())
    def test_non_student_receives_no_contest_content(self, client, non_student, url):
        ContestFactory(title="Concours Secret", slug="slug-test")
        client.force_login(non_student)
        response = client.get(url, follow=True)

        assert "Concours Secret" not in response.content.decode()

    def test_staff_but_not_student_is_blocked(self, client):
        """Un membre du staff non étudiant reste bloqué sur les concours."""
        staff = UserFactory.create(is_staff=True, is_student=False)
        ContestFactory(slug="slug-test")
        client.force_login(staff)

        response = client.get(reverse("contest:list"))

        assert response.status_code == 302
        assert response["Location"].startswith(reverse("users:profile"))


@pytest.mark.django_db
class TestContestAccessStudent:
    """L'étudiant inscrit conserve l'accès complet."""

    def test_student_can_view_list(self, client, student):
        contest = ContestFactory(title="Concours Ouvert")
        client.force_login(student)

        response = client.get(reverse("contest:list"))

        assert response.status_code == 200
        assert contest.title in response.content.decode()

    def test_student_can_view_detail(self, client, student):
        contest = ContestFactory(title="Concours Ouvert")
        client.force_login(student)

        response = client.get(
            reverse("contest:detail", kwargs={"slug": contest.slug}),
        )

        assert response.status_code == 200
        assert "Concours Ouvert" in response.content.decode()


@pytest.mark.django_db
class TestHomeContestDisclosure:
    """L'accueil ne doit exposer aucune donnée de concours hors étudiants."""

    def test_home_hides_contests_from_anonymous(self, client):
        ContestFactory(title="Concours Secret")
        response = client.get(reverse("home"))

        assert response.status_code == 200
        assert "Concours Secret" not in response.content.decode()

    def test_home_hides_contests_from_non_student(self, client, non_student):
        ContestFactory(title="Concours Secret")
        client.force_login(non_student)
        response = client.get(reverse("home"))

        assert response.status_code == 200
        assert "Concours Secret" not in response.content.decode()

    def test_home_shows_contests_to_student(self, client, student):
        contest = ContestFactory(title="Concours Ouvert")
        client.force_login(student)
        response = client.get(reverse("home"))

        assert response.status_code == 200
        assert contest.title in response.content.decode()
