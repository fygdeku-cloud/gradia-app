from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from django.test import Client
from django.urls import reverse

from gradia.users.models import StudentProfile
from gradia.users.otp_utils import OtpUtils
from gradia.users.services import OtpService
from gradia.users.tests.factories import UserFactory
from gradia.utils.enums import OtpPurpose

PASSWORD = "Passw0rd!2024"
OTP_CODE = "123456"


@pytest.fixture
def deterministic_otp(monkeypatch):
    from gradia.users.otp_utils import OtpUtils as OTU

    monkeypatch.setattr(OTU, "generate_code", staticmethod(lambda: OTP_CODE))


def _qs(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


class TestLoginView:
    def test_get_login_page(self, db):
        response = Client().get(reverse("users:login"))
        assert response.status_code == 200

    def test_verified_user_logs_in(self, db):
        user = UserFactory.create()
        response = Client().post(
            reverse("users:login"),
            {"email": user.email, "password": PASSWORD},
        )
        assert response.status_code == 302
        assert reverse("users:profile") in response["Location"]

    def test_login_with_next_url(self, db):
        user = UserFactory.create()
        response = Client().post(
            reverse("users:login"),
            {"email": user.email, "password": PASSWORD, "next": "/cart/"},
        )
        assert response.status_code == 302
        assert response["Location"] == "/cart/"

    def test_login_bad_credentials(self, db):
        response = Client().post(
            reverse("users:login"),
            {"email": "nobody@example.com", "password": "wrong"},
        )
        assert response.status_code == 200

    def test_unverified_user_redirected_to_otp(self, db, deterministic_otp):
        user = UserFactory.create(email_verified=False)
        response = Client().post(
            reverse("users:login"),
            {"email": user.email, "password": PASSWORD},
        )
        assert response.status_code == 302
        location = response["Location"]
        assert reverse("users:verify_email") in location
        params = _qs(location)
        assert params["purpose"] == [OtpPurpose.LOGIN]
        assert params["token"][0]

    def test_unverified_login_carries_next(self, db, deterministic_otp):
        user = UserFactory.create(email_verified=False)
        response = Client().post(
            reverse("users:login") + "?next=/documents/",
            {"email": user.email, "password": PASSWORD},
        )
        location = response["Location"]
        params = _qs(location)
        assert params["next"] == ["/documents/"]


class TestRegisterView:
    def test_get_register_page(self, db):
        response = Client().get(reverse("users:register"))
        assert response.status_code == 200

    def test_register_creates_student_and_redirects_to_otp(self, db, deterministic_otp):
        client = Client()
        response = client.post(
            reverse("users:register"),
            {
                "email": "newbie@example.com",
                "name": "Nouvel Étudiant",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        assert response.status_code == 302
        assert reverse("users:verify_email") in response["Location"]
        params = _qs(response["Location"])
        assert params["token"][0]

        from gradia.users.models import User

        user = User.objects.get(email="newbie@example.com")
        assert user.email_verified is False
        assert StudentProfile.objects.filter(user=user).exists()

    def test_register_duplicate_email_rejected(self, db):
        UserFactory.create(email="duplicate@example.com")
        response = Client().post(
            reverse("users:register"),
            {
                "email": "DUPLICATE@example.com",
                "name": "Doublon",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        assert response.status_code == 200


class TestEmailVerificationView:
    def test_signup_verification_logs_in_and_redirects_to_profile(self, db, deterministic_otp):
        from gradia.users.models import User

        client = Client()
        response = client.post(
            reverse("users:register"),
            {
                "email": "student@example.com",
                "name": "Étudiant",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        token = _qs(response["Location"])["token"][0]

        response = client.post(
            reverse("users:verify_email"),
            {"purpose": OtpPurpose.SIGNUP, "token": token, "code": OTP_CODE},
        )
        assert response.status_code == 302
        assert reverse("users:profile") in response["Location"]
        user = User.objects.get(email="student@example.com")
        user.refresh_from_db()
        assert user.email_verified is True

    def test_login_verification_without_next_goes_to_profile(self, db, deterministic_otp):
        user = UserFactory.create(email_verified=False)
        client = Client()
        location = client.post(
            reverse("users:login"),
            {"email": user.email, "password": PASSWORD},
        )["Location"]
        params = _qs(location)

        response = client.post(
            reverse("users:verify_email"),
            {"purpose": OtpPurpose.LOGIN, "token": params["token"][0], "code": OTP_CODE},
        )
        # Régression U2 : après vérification, on ne doit plus être renvoyé
        # vers la page de vérification elle-même (boucle via le référent).
        assert response.status_code == 302
        assert response["Location"] == reverse("users:profile")

    def test_login_verification_honors_next(self, db, deterministic_otp):
        user = UserFactory.create(email_verified=False)
        client = Client()
        location = client.post(
            reverse("users:login") + "?next=/cart/",
            {"email": user.email, "password": PASSWORD},
        )["Location"]
        params = _qs(location)

        response = client.post(
            reverse("users:verify_email"),
            {
                "purpose": OtpPurpose.LOGIN,
                "token": params["token"][0],
                "code": OTP_CODE,
                "next": "/cart/",
            },
        )
        assert response.status_code == 302
        assert response["Location"] == "/cart/"

    def test_wrong_code_shows_error(self, db, deterministic_otp):
        user = UserFactory.create(email_verified=False)
        client = Client()
        location = client.post(
            reverse("users:login"),
            {"email": user.email, "password": PASSWORD},
        )["Location"]
        params = _qs(location)

        response = client.post(
            reverse("users:verify_email"),
            {"purpose": OtpPurpose.LOGIN, "token": params["token"][0], "code": "999999"},
        )
        assert response.status_code == 200
        assert any(
            m.level_tag == "error" for m in list(response.context["messages"])
        )


class TestResendVerificationView:
    def test_resend_after_cooldown(self, db, deterministic_otp):
        from django.core import mail

        user = UserFactory.create(email_verified=False)
        client = Client()
        location = client.post(
            reverse("users:login"),
            {"email": user.email, "password": PASSWORD},
        )["Location"]
        token = _qs(location)["token"][0]

        OtpUtils.clear_cooldown(user.pk, OtpPurpose.LOGIN)
        mail.outbox.clear()

        response = client.post(
            reverse("users:resend_verification"),
            {"purpose": OtpPurpose.LOGIN, "token": token},
        )
        assert response.status_code == 302
        assert reverse("users:verify_email") in response["Location"]
        assert len(mail.outbox) == 1

    def test_resend_on_cooldown_shows_error(self, db, deterministic_otp):
        user = UserFactory.create(email_verified=False)
        client = Client()
        location = client.post(
            reverse("users:login"),
            {"email": user.email, "password": PASSWORD},
        )["Location"]
        token = _qs(location)["token"][0]

        response = client.post(
            reverse("users:resend_verification"),
            {"purpose": OtpPurpose.LOGIN, "token": token},
        )
        assert response.status_code == 302
        assert "verify-email" in response["Location"]