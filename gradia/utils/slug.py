    
"""
Utilitaires de génération de slugs pour Gradia.
"""

from __future__ import annotations

import logging
import secrets
import string
from typing import Any

from django.utils.text import slugify


logger = logging.getLogger(__name__)


class DbFunctions:
    """Utilitaires génériques liés aux valeurs uniques."""

    RANDOM_SUFFIX_LENGTH = 6

    RANDOM_CHARS = (
        string.ascii_lowercase
        + string.digits
    )

    @staticmethod
    def random_string_generator(
        size: int = RANDOM_SUFFIX_LENGTH,
        chars: str = RANDOM_CHARS,
    ) -> str:
        """Génère une chaîne aléatoire sécurisée."""

        return "".join(
            secrets.choice(chars)
            for _ in range(size)
        )

    @staticmethod
    def _get_slug_max_length(
        instance: Any,
    ) -> int:
        """Récupère la longueur maximale du champ slug."""

        try:
            field = instance.__class__._meta.get_field(
                "slug"
            )
        except Exception as exc:
            msg = (
                f"Le modèle "
                f"{instance.__class__.__name__!r} "
                f"doit définir un champ 'slug'."
            )

            raise AttributeError(msg) from exc

        if field.max_length is None:
            raise ValueError(
                "Le champ slug doit définir max_length."
            )

        return field.max_length

    @staticmethod
    def generate_unique_slug(
        instance: Any,
        field_value: str,
        max_attempts: int = 100,
    ) -> str:
        """Génère un slug globalement unique."""

        if not field_value:
            raise ValueError(
                "La valeur utilisée pour générer le slug "
                "ne peut pas être vide."
            )

        max_length = (
            DbFunctions._get_slug_max_length(
                instance
            )
        )

        base_slug = slugify(
            field_value
        )[:max_length]

        candidate = base_slug

        for attempt in range(max_attempts):
            queryset = instance.__class__.objects.filter(
                slug=candidate
            )

            if instance.pk:
                queryset = queryset.exclude(
                    pk=instance.pk
                )

            if not queryset.exists():
                return candidate

            suffix = (
                DbFunctions.random_string_generator()
            )

            trim_length = (
                max_length
                - DbFunctions.RANDOM_SUFFIX_LENGTH
                - 1
            )

            candidate = (
                f"{base_slug[:trim_length]}"
                f"-{suffix}"
            )

        raise ValueError(
            "Impossible de générer un slug unique "
            f"pour {instance.__class__.__name__!r}."
        )

    @staticmethod
    def generate_unique_slug_for_related_object(
        instance: Any,
        field_value: str,
        related_field_name: str,
        max_attempts: int = 100,
    ) -> str:
        """Génère un slug unique dans le contexte d'un parent."""

        max_length = (
            DbFunctions._get_slug_max_length(
                instance
            )
        )

        try:
            related_instance = getattr(
                instance,
                related_field_name,
            )
        except AttributeError as exc:
            raise AttributeError(
                f"Le champ {related_field_name!r} "
                f"n'existe pas sur "
                f"{instance.__class__.__name__!r}."
            ) from exc

        base_slug = slugify(
            field_value
        )[:max_length]

        candidate = base_slug

        for _ in range(max_attempts):
            filters = {
                "slug": candidate,
                related_field_name: related_instance,
            }

            queryset = instance.__class__.objects.filter(
                **filters
            )

            if instance.pk:
                queryset = queryset.exclude(
                    pk=instance.pk
                )

            if not queryset.exists():
                return candidate

            suffix = (
                DbFunctions.random_string_generator()
            )

            trim_length = (
                max_length
                - DbFunctions.RANDOM_SUFFIX_LENGTH
                - 1
            )

            candidate = (
                f"{base_slug[:trim_length]}"
                f"-{suffix}"
            )

        raise ValueError(
            "Impossible de générer un slug unique."
        )

    @staticmethod
    def unique_slug_generator_by_name(
        instance: Any,
    ) -> str:
        """Génère un slug unique à partir du champ name."""

        if not hasattr(instance, "name"):
            raise AttributeError(
                f"Le modèle "
                f"{instance.__class__.__name__!r} "
                "doit posséder un attribut 'name'."
            )

        return DbFunctions.generate_unique_slug(
            instance,
            instance.name,
        )