"""
Stockages sécurisés du module Document.

Ces stockages éloignent physiquement les fichiers des documents de la racine
média publique (`MEDIA_ROOT`) afin qu'aucune URL directe ne puisse jamais
exposer un fichier protégé (sujet ou corrigé).

L'accès aux fichiers passe exclusivement par des vues Django contrôlées
"""

from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from storages.backends.s3boto3 import S3Boto3Storage



class ProtectedDocumentStorage:
    """
    Factory pour le stockage sécurisé des documents.
    """

    def __new__(cls, **kwargs):
        if settings.USE_S3_STORAGE:
            if S3Boto3Storage is None:
                raise ImportError("django-storages est requis pour utiliser S3.")

            class S3ProtectedStorage(S3Boto3Storage):
                def __init__(self, **kwargs):
                    super().__init__(
                        bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                        region_name=settings.AWS_S3_REGION_NAME,
                        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                        access_key=settings.AWS_ACCESS_KEY_ID,
                        secret_key=settings.AWS_SECRET_ACCESS_KEY,
                        default_acl="private",
                        **kwargs,
                    )

                def url(self, name):
                    # Ne jamais exposer l'URL du fichier protégé.
                    return ""

            return S3ProtectedStorage(**kwargs)
        else:

            class LocalProtectedStorage(FileSystemStorage):
                def __init__(self, **kwargs):
                    location = getattr(
                        settings,
                        "PROTECTED_MEDIA_ROOT",
                        kwargs.pop("location", None),
                    )
                    super().__init__(location=location, base_url=None, **kwargs)

                def url(self, name):
                    # Ne jamais exposer le chemin du fichier protégé.
                    return ""

            return LocalProtectedStorage(**kwargs)


# Instance réutilisable par les champs de modèle.
protected_document_storage = ProtectedDocumentStorage()
