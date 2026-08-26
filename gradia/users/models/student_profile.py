from django.conf import settings
from django.db import models
from gradia.core.models import TimeStampedModel
from phonenumber_field.modelfields import PhoneNumberField
from gradia.core.validators.phone import validate_phone_number


class StudentProfile(TimeStampedModel):
    # Champs requis pour le profil d'un etudiant
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    phone_number = models.CharField(max_length=20, blank=True, validators=[validate_phone_number])
    school = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Student Profile -{self.user.email}"
