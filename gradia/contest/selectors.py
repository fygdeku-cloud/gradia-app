from django.db.models import Count

from gradia.contest.models import (
    Contest,
    ContestSession,
    Establishment,
)


def get_contests():
    """Liste des concours avec leurs relations principales préchargées."""
    return (
        Contest.objects.select_related("establishment", "category")
        .prefetch_related("sessions")
        .order_by("title")
    )


def get_contest_detail(slug):
    """Détail d'un concours (None si aucune correspondance)."""
    return (
        Contest.objects.select_related("establishment", "category")
        .prefetch_related("sessions")
        .filter(slug=slug)
        .first()
    )


def get_establishments():
    """Liste des établissements avec le nombre de concours associés."""
    return (
        Establishment.objects.annotate(contest_count=Count("contests"))
        .order_by("title")
    )


def get_establishment_detail(slug):
    """Détail d'un établissement (None si aucune correspondance)."""
    return (
        Establishment.objects.annotate(
            contest_count=Count("contests")
        )
        .filter(slug=slug)
        .first()
    )


def get_establishment_contests(establishment):
    """Concours d'un établissement avec catégorie et sessions."""
    return (
        establishment.contests.select_related("category")
        .prefetch_related("sessions")
        .order_by("title")
    )


def get_session_detail(contest_slug, year):
    """Détail d'une session de concours (None si aucune correspondance)."""
    return (
        ContestSession.objects.select_related(
            "contest__establishment",
            "contest__category",
        )
        .filter(contest__slug=contest_slug, year=year)
        .first()
    )


def get_session_documents(session):
    """Documents rattachés à une session de concours."""
    return session.documents.all()