from django.db import models

# Classe de base pour les modèles avec des champs de date de création et de mise à jour
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
