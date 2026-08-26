from django.db import models
import uuid

# Classe de base pour les modèles avec des champs de date de création et de mise à jour
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# Classe de base pour les modèles qui necessitent un UUID
class UUIDModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        abstract = True
        
# Classe de base
class BaseModel(UUIDModel, TimeStampedModel):

    class Meta:
        abstract = True
