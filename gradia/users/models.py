from django.contrib.auth.models import AbstractUser
from gradia.users.managers import UserManager
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from gradia.core.models import BaseModel
from django.conf import settings
from django.db import models
from gradia.users.validator import validate_phone_number
from gradia.utils.enums import OtpPurpose
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import check_password, make_password



class User(AbstractUser, BaseModel):
    # Champs necessaires pour nos users
    email = models.EmailField(_("Email"), unique=True)
    first_name = None
    last_name = None
    name = models.CharField(_("Name"), max_length=255, blank=True)
    is_student = models.BooleanField(_("Is Student"), default=True)
    is_admin = models.BooleanField(_("Is Admin"), default=False)
    email_verified = models.BooleanField(_("Email Verified"), default=False)
    
    # L'email devient l'identifiant necessaire pour notre authentification
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
            verbose_name = _("User")
            verbose_name_plural = _("Users")
    
    def __str__(self):
        return self.email

    @property
    def is_privileged(self):
        """Comptes administrateurs exemptés de la vérification d'e-mail."""
        return self.is_superuser or self.is_staff

    @property
    def requires_email_verification(self):
        """
        La vérification d'e-mail ne s'applique jamais au superutilisateur
        (ni au staff) : ces comptes sont automatiquement validés.
        """
        if self.is_privileged:
            return False
        return not self.email_verified

    def auto_validate_email(self):
        """Marque l'e-mail comme vérifié sans passer par l'OTP (comptes privilégiés)."""
        if self.email_verified:
            return
        self.email_verified = True
        self.save(update_fields=["email_verified"])


class StudentProfile(BaseModel):
    # Champs requis pour le profil d'un etudiant
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name = _("User"), on_delete=models.CASCADE, related_name="student_profile")
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True, validators=[validate_phone_number])
    school = models.CharField(_("School"), max_length=255, blank=True)

    class Meta:
            verbose_name = _("Student Profile")
            verbose_name_plural = _("Student Profiles")
    # Representation en string du profil de l'etudiant
    def __str__(self):
        return f"Student Profile -{self.user.email}"


class Otp(BaseModel):
    """
    OTP générique utilisé pour les opérations sensibles
    liées à l'authentification.
    """
    
    DEFAULT_MAX_ATTEMPTS = 5
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="otps")
    purpose = models.CharField(max_length=30, choices=OtpPurpose.choices)
    code_hash = models.CharField(max_length=255)
    expiration_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["user", "purpose", "is_used"],
            ),
            models.Index(
                fields=["expiration_at"],
            ),
        ]

    def __str__(self):
        return f"OTP {self.user.email} - {self.purpose}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expiration_at

    @property
    def can_attempt(self):
        return (
            not self.is_used
            and not self.is_expired
            and self.attempts < self.DEFAULT_MAX_ATTEMPTS
        )

    def set_code(self, code: str):
        """
        Stocke uniquement le hash du code OTP.
        Le code en clair n'est jamais enregistré en base.
        """
        self.code_hash = make_password(code)

    def is_valid_code(self, code: str) -> bool:
        """
        Vérifie le code OTP fourni contre son hash.
        """
        if not self.can_attempt:
            return False

        return check_password(
            code,
            self.code_hash,
        )

    def increment_attempts(self):
        self.attempts += 1
        self.save(
            update_fields=["attempts"],
        )

    def mark_verified(self):
        self.is_used = True
        self.used_at = timezone.now()

        self.save(
            update_fields=[
                "is_used",
                "used_at",
            ],
        )

    def invalidate(self):
        self.is_used = True
        self.used_at = timezone.now()

        self.save(
            update_fields=[
                "is_used",
                "used_at",
            ],
        )
