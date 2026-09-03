from django import forms
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import StudentProfile, User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    """Formulaire de modification d'un utilisateur depuis l'administration."""

    class Meta:
        model = User
        fields = "__all__"


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """Formulaire de création d'un utilisateur depuis l'administration."""

    class Meta:
        model = User
        fields = "__all__"


class UserSignupForm(forms.ModelForm):
    """Formulaire d'inscription d'un nouvel utilisateur."""

    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        strip=False,
    )

    password2 = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput,
        strip=False,
    )

    class Meta:
        model = User
        fields = (
            "email",
            "name",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                _("A user with this email address already exists.")
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError(
                _("The two passwords do not match.")
            )

        if password1:
            try:
                validate_password(password1)
            except ValidationError as e:
                self.add_error("password1", e)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        user.username = User.objects._generate_unique_username(
            self.cleaned_data["email"]
        )

        user.set_password(
            self.cleaned_data["password1"]
        )

        user.is_student = True
        user.is_admin = False
        user.email_verified = False

        if commit:
            user.save()

        return user


class UserLoginForm(forms.Form):
    """Formulaire de connexion avec l'adresse email."""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
            }
        ),
    )

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
            }
        ),
    )

    error_messages = {
        "invalid_login": _(
            "Please enter a correct email and password."
        ),
        "inactive": _(
            "This account is inactive."
        ),
    }

    user = None

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            self.user = authenticate(username=email, password=password)
            if self.user is None:
                raise ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )
            if not self.user.is_active:
                raise ValidationError(
                    self.error_messages["inactive"],
                    code="inactive",
                )
        return cleaned_data

    def get_user(self):
        return self.user


class EmailVerificationForm(forms.Form):
    """Formulaire de vérification d'une adresse email avec token."""

    token = forms.CharField(widget=forms.HiddenInput, required=False)

    code = forms.CharField(
        label=_("Verification code"),
        max_length=6,
        min_length=6,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "maxlength": "6",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()

        if not code.isdigit():
            raise ValidationError(
                _("The verification code must contain only digits.")
            )

        return code


class ResendVerificationForm(forms.Form):
    """Formulaire de demande de renvoi du code de vérification."""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
            }
        ),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class PasswordResetRequestForm(forms.Form):
    """Formulaire de demande de réinitialisation du mot de passe."""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
            }
        ),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class SetNewPasswordForm(forms.Form):
    """Formulaire permettant de définir un nouveau mot de passe."""

    token = forms.CharField(widget=forms.HiddenInput, required=False)

    password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
            }
        ),
    )

    password2 = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError(
                _("The two passwords do not match.")
            )

        if password1:
            try:
                validate_password(password1)
            except ValidationError as e:
                self.add_error("password1", e)

        return cleaned_data


class StudentProfileForm(forms.ModelForm):
    """Formulaire de modification du profil étudiant."""

    class Meta:
        model = StudentProfile
        fields = (
            "phone_number",
            "school",
        )
