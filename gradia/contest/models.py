from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from gradia.core.models import BaseModel, TitleDescriptionModel
from django.utils.translation import gettext_lazy as _


class Establishment(BaseModel, TitleDescriptionModel):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ["title"]
        verbose_name = _("Établissement")
        verbose_name_plural = _("Établissements")

    def __str__(self):
        return self.title

    def get_contests(self):
        return self.contests.all()
        
       
class ContestCategory(BaseModel, TitleDescriptionModel):
  
    class Meta:
        ordering = ["title"]
        verbose_name = _("Catégorie de concours")
        verbose_name_plural = _("Catégories de concours")

    def __str__(self):
        return self.title

    def get_contests(self):
        return self.contests.all()    


class Contest(BaseModel, TitleDescriptionModel):
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    requirements = models.TextField(blank=True)
    establishment = models.ForeignKey(Establishment, on_delete=models.PROTECT, related_name="contests")
    category = models.ForeignKey(ContestCategory, on_delete=models.PROTECT, related_name="contests")

    class Meta:
        ordering = ["title"]
        verbose_name = _("Concours")
        verbose_name_plural = _("Concours")
        constraints = [
            models.UniqueConstraint(fields=["establishment", "title"], name="unique_contest_per_establishment")
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(
                f"{self.establishment.title}-{self.title}"
            )

        super().save(*args, **kwargs)

    def get_contest_sessions(self):
        return self.sessions.all()

    def get_absolute_url(self):
        return reverse(
            "contest:detail",
            kwargs={"slug": self.slug},
        )
 
        
class ContestSession(BaseModel, TitleDescriptionModel):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="sessions")
    year = models.PositiveIntegerField()
    registration_start_date = models.DateField( null=True, blank=True)
    registration_end_date = models.DateField( null=True, blank=True)
    exam_date = models.DateField( null=True, blank=True)
    
    class Meta:
        ordering = ["-year"]
        verbose_name = "Session de concours"
        verbose_name_plural = "Sessions de concours"
        constraints = [
            models.UniqueConstraint( fields=["contest", "year"], name="unique_contest_session_year")
        ]

    def __str__(self):
        return f"{self.contest.title} - Session {self.title}"

    def get_documents(self):
        return self.documents.all()

    def get_absolute_url(self):
        return reverse(
            "contest:session_detail",
            kwargs={
                "contest_slug": self.contest.slug,
                "year": self.year,
            },
        )        
