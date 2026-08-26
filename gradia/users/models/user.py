from django.contrib.auth.models import AbstractUser
from django.db import models
from gradia.users.managers.user import UserManager


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