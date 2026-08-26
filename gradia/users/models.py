from django.contrib.auth.models import AbstractUser
from gradia.users.managers import UserManager
from datetime import timedelta
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from gradia.core.models import BaseModel
from django.conf import settings
from django.db import models
from gradia.core.models import TimeStampedModel
from gradia.users.validators import validate_phone_number


class User(AbstractUser):
    # Champs necessaires pour nos users
    email = models.EmailField(unique=True)
    first_name = None
    last_name = None
    is_student = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    # L'email devient l'identifiant necessaire pour notre authentification
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.email
    

class StudentProfile(TimeStampedModel):
    # Champs requis pour le profil d'un etudiant
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    phone_number = models.CharField(max_length=20, blank=True, validators=[validate_phone_number])
    school = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Student Profile -{self.user.email}"


class EmailVerification(BaseModel):
    # Champs de verification de l'email
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_verification")
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Email verification"
        verbose_name_plural = "Email verifications"

    def __str__(self):
        return f"Email verification - {self.user.email}"

    @property
    def is_verified(self):
        return self.verified_at is not None

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.is_verified and not self.is_expired

    # Chargement du code
    def set_code(self, code, expiration_minutes=10):
        self.code_hash = make_password(code)
        self.expires_at = timezone.now() + timedelta(minutes=expiration_minutes)
        self.verified_at = None
        self.attempts = 0
        self.sent_at = timezone.now()

    # Verification du code 
    def verify_code(self, code, max_attempts=5):
        if self.is_verified:
            return False

        if self.is_expired:
            return False

        if self.attempts >= max_attempts:
            return False

        self.attempts += 1
        
        # Verification du password
        if not check_password(code, self.code_hash):
            self.save(
                update_fields=[
                    "attempts",
                    "updated_at",
                ]
            )
            return False
        self.verified_at = timezone.now()
        self.save(
            update_fields=[
                "attempts",
                "verified_at",
                "updated_at",
            ]
        )
        return True
    
