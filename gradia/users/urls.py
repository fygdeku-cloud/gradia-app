from django.urls import path

from .views.login_views import LoginView
from .views.logout_views import LogoutView
from .views.password_views import (
    PasswordResetRequestView,
    PasswordResetConfirmView,
)
from .views.profil_views import ProfileView
from .views.register_views import RegisterView
from .views.verification_views import (
    EmailVerificationView,
    ResendVerificationView,
)


app_name = "users"


urlpatterns = [
    # Authentication
    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),
    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),

    # Email verification
    path(
        "verify-email/",
        EmailVerificationView.as_view(),
        name="verify_email",
    ),
    path(
        "resend-verification/",
        ResendVerificationView.as_view(),
        name="resend_verification",
    ),

    # Profile
    path(
        "profile/",
        ProfileView.as_view(),
        name="profile",
    ),

    # Password reset
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]