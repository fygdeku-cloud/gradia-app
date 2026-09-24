from __future__ import annotations

import pytest

from gradia.users.models import Otp
from gradia.users.otp_utils import OtpUtils
from gradia.users.services import (
    OtpRateLimitError,
    OtpService,
    OtpVerificationError,
    OtpVerifyService,
)
from gradia.utils.enums import OtpPurpose


def make_otp(user, db):
    otp, token = OtpService.create(user, OtpPurpose.LOGIN)
    return otp, token


class TestOtpService:
    def test_invalid_purpose_rejected(self, db, student):
        with pytest.raises(ValueError):
            OtpService.create(student, "invalid")

    def test_create_returns_otp_and_token(self, db, student):
        otp, token = make_otp(student, db)
        assert otp.user == student
        assert otp.purpose == OtpPurpose.LOGIN
        assert otp.is_used is False
        assert token
        assert getattr(otp, "_raw_code", None)

    def test_create_on_cooldown_raises(self, db, student):
        OtpUtils.start_cooldown(student.pk, OtpPurpose.LOGIN)
        with pytest.raises(OtpRateLimitError):
            OtpService.create(student, OtpPurpose.LOGIN)

    def test_create_invalidates_previous_otps(self, db, student):
        first, _token = make_otp(student, db)
        second, _token = make_otp(student, db)
        first.refresh_from_db()
        assert first.is_used is True
        assert second.is_used is False


class TestOtpVerifyService:
    def test_verify_with_valid_code(self, db, student):
        otp, token = make_otp(student, db)
        verified = OtpVerifyService.verify(
            token=token,
            code=otp._raw_code,
            purpose=OtpPurpose.LOGIN,
        )
        assert verified.is_used is True
        assert verified.used_at is not None
        otp.user.refresh_from_db()
        assert otp.user.email_verified is True

    def test_verify_rejects_used_code(self, db, student):
        otp, token = make_otp(student, db)
        OtpVerifyService.verify(
            token=token, code=otp._raw_code, purpose=OtpPurpose.LOGIN
        )
        with pytest.raises(OtpVerificationError):
            OtpVerifyService.verify(
                token=token, code=otp._raw_code, purpose=OtpPurpose.LOGIN
            )

    def test_verify_wrong_code_increments_attempts(self, db, student):
        otp, token = make_otp(student, db)
        with pytest.raises(OtpVerificationError):
            OtpVerifyService.verify(
                token=token, code="000000", purpose=OtpPurpose.LOGIN
            )
        otp.refresh_from_db()
        assert otp.attempts == 1
        assert otp.is_used is False

    def test_verify_expired_code(self, db, student):
        otp, token = make_otp(student, db)
        from django.utils import timezone

        from datetime import timedelta

        Otp.objects.filter(pk=otp.pk).update(
            expiration_at=timezone.now() - timedelta(minutes=1)
        )
        with pytest.raises(OtpVerificationError):
            OtpVerifyService.verify(
                token=token, code=otp._raw_code, purpose=OtpPurpose.LOGIN
            )

    def test_verify_wrong_token_purpose(self, db, student):
        otp, token = make_otp(student, db)
        with pytest.raises(OtpVerificationError):
            OtpVerifyService.verify(
                token=token, code=otp._raw_code, purpose=OtpPurpose.SIGNUP
            )

    def test_verify_tampered_token(self, db, student):
        with pytest.raises(OtpVerificationError):
            OtpVerifyService.verify(
                token="forged.token.value", code="123456", purpose=OtpPurpose.LOGIN
            )