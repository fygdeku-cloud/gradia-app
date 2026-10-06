import pytest

from gradia.users.api.serializers import UserSerializer


@pytest.mark.django_db
class TestUserSerializer:
    def test_privilege_fields_are_read_only(self, student):
        serializer = UserSerializer(
            student,
            data={"is_admin": True, "is_student": False, "email_verified": True},
            partial=True,
        )

        assert serializer.is_valid(), serializer.errors
        assert "is_admin" not in serializer.validated_data
        assert "is_student" not in serializer.validated_data
        assert "email_verified" not in serializer.validated_data

    def test_update_cannot_escalate_privileges(self, student):
        serializer = UserSerializer(
            student,
            data={"is_admin": True, "name": "Hacker"},
            partial=True,
        )

        assert serializer.is_valid(), serializer.errors
        serializer.save()
        student.refresh_from_db()

        assert student.is_admin is False
        assert student.name == "Hacker"