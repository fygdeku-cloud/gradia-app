from django.db import models
import uuid


# Classe de base
class BaseModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class TitleDescriptionModel(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    class Meta:
        abstract = True
