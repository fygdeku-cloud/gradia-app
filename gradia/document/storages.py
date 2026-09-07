"""
Stockages sécurisés du module Document.
"""

from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage


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
        return ""

class LocalProtectedStorage(FileSystemStorage):
    def __init__(self, **kwargs):
        location = getattr(
            settings,
            "PROTECTED_MEDIA_ROOT",
            kwargs.pop("location", None),
        )
        super().__init__(location=location, base_url=None, **kwargs)

    def url(self, name):
        return ""

class ProtectedDocumentStorage(FileSystemStorage):
    """
    Stockage sécurisé qui sélectionne dynamiquement le backend.
    """
    def __init__(self, *args, **kwargs):
        if settings.USE_S3_STORAGE:
            self.backend = S3ProtectedStorage(*args, **kwargs)
        else:
            self.backend = LocalProtectedStorage(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def _save(self, name, content):
        return self.backend._save(name, content)

    def _open(self, name, mode='rb'):
        return self.backend._open(name, mode)

    def url(self, name):
        return self.backend.url(name)
        
    def exists(self, name):
        return self.backend.exists(name)

    def delete(self, name):
        return self.backend.delete(name)

    def deconstruct(self):
        return ("gradia.document.storages.ProtectedDocumentStorage", [], {})


# Instance réutilisable par les champs de modèle.
protected_document_storage = ProtectedDocumentStorage()
