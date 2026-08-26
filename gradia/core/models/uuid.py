import uuid
from django.db import models

# Classe de base pour les modèles qui necessitent un UUID
class UUIDModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        abstract = True
        