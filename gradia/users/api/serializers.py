from rest_framework import serializers

from gradia.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["pk", "email", "name", "is_student", "is_admin", "email_verified"]

        extra_kwargs = {
            "pk": {"read_only": True},
            "is_student": {"read_only": True},
            "is_admin": {"read_only": True},
            "email_verified": {"read_only": True},
        }
