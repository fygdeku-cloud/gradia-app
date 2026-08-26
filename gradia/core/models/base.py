from .timestamps import TimeStampedModel
from .uuid import UUIDModel

# Classe de base
class BaseModel(UUIDModel, TimeStampedModel):

    class Meta:
        abstract = True
        