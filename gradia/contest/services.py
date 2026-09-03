from django.core.exceptions import ValidationError

from gradia.contest.models import (
    Contest,
    ContestCategory,
    ContestSession,
    Establishment,
)


class EstablishmentService:
    """
    Opérations métier liées aux établissements.
    """

    @staticmethod
    def create(
        *,
        title: str,
        description: str = "",
        location: str = "",
        name: str | None = None,
    ) -> Establishment:
        if not title or not title.strip():
            raise ValidationError(
                {"title": "Le titre de l'établissement est obligatoire."}
            )

        establishment = Establishment(
            title=title.strip(),
            description=description,
            location=location,
            name=name or title.strip(),
        )
        establishment.full_clean()
        establishment.save()
        return establishment

    @staticmethod
    def update(
        establishment: Establishment,
        *,
        title: str | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> Establishment:
        if title is not None:
            establishment.title = title
        if description is not None:
            establishment.description = description
        if location is not None:
            establishment.location = location

        establishment.full_clean()
        establishment.save()
        return establishment


class CategoryService:
    """
    Opérations métier liées aux catégories de concours.
    """

    @staticmethod
    def create(
        *,
        title: str,
        description: str = "",
    ) -> ContestCategory:
        if not title or not title.strip():
            raise ValidationError(
                {"title": "Le titre de la catégorie est obligatoire."}
            )

        category = ContestCategory(
            title=title.strip(),
            description=description,
        )
        category.full_clean()
        category.save()
        return category

    @staticmethod
    def update(
        category: ContestCategory,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> ContestCategory:
        if title is not None:
            category.title = title
        if description is not None:
            category.description = description

        category.full_clean()
        category.save()
        return category


class ContestService:
    """
    Opérations métier liées aux concours.
    """

    @staticmethod
    def create(
        *,
        title: str,
        establishment: Establishment,
        category: ContestCategory,
        description: str = "",
        requirements: str = "",
    ) -> Contest:
        if not title or not title.strip():
            raise ValidationError(
                {"title": "Le titre du concours est obligatoire."}
            )

        contest = Contest(
            title=title.strip(),
            description=description,
            requirements=requirements,
            establishment=establishment,
            category=category,
        )
        contest.full_clean()
        contest.save()
        return contest

    @staticmethod
    def update(
        contest: Contest,
        *,
        title: str | None = None,
        description: str | None = None,
        requirements: str | None = None,
        establishment: Establishment | None = None,
        category: ContestCategory | None = None,
    ) -> Contest:
        if title is not None:
            contest.title = title
        if description is not None:
            contest.description = description
        if requirements is not None:
            contest.requirements = requirements
        if establishment is not None:
            contest.establishment = establishment
        if category is not None:
            contest.category = category

        contest.full_clean()
        contest.save()
        return contest


class SessionService:
    """
    Opérations métier liées aux sessions de concours.
    """

    @staticmethod
    def create(
        *,
        contest: Contest,
        year: int,
        title: str,
        description: str = "",
        registration_start_date=None,
        registration_end_date=None,
        exam_date=None,
    ) -> ContestSession:
        if not title or not title.strip():
            raise ValidationError(
                {"title": "Le titre de la session est obligatoire."}
            )

        session = ContestSession(
            contest=contest,
            year=year,
            title=title.strip(),
            description=description,
            registration_start_date=registration_start_date,
            registration_end_date=registration_end_date,
            exam_date=exam_date,
        )
        session.full_clean()
        session.save()
        return session

    @staticmethod
    def update(
        session: ContestSession,
        *,
        title: str | None = None,
        description: str | None = None,
        year: int | None = None,
        registration_start_date=None,
        registration_end_date=None,
        exam_date=None,
    ) -> ContestSession:
        if title is not None:
            session.title = title
        if description is not None:
            session.description = description
        if year is not None:
            session.year = year
        if registration_start_date is not None:
            session.registration_start_date = registration_start_date
        if registration_end_date is not None:
            session.registration_end_date = registration_end_date
        if exam_date is not None:
            session.exam_date = exam_date

        session.full_clean()
        session.save()
        return session