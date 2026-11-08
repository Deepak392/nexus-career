import os

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        trim_whitespace=False,
    )

    email = serializers.EmailField(
        required=True,
        allow_blank=False,
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        allowed_domain = os.getenv(
            "STUDENT_EMAIL_DOMAIN",
            "scds.saiuniversity.edu.in",
        ).strip().lower().lstrip("@")
        email_domain = normalized_email.rpartition("@")[2]

        if email_domain != allowed_domain:
            raise serializers.ValidationError(
                "Student registration requires an authorized university "
                f"email address ending in @{allowed_domain}."
            )

        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError(
                "An account with this email address already exists."
            )

        return normalized_email

    def create(self, validated_data):
        return User.objects.create_user(
            **validated_data,
            role=User.Role.STUDENT,
        )


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "is_verified",
        ]
        read_only_fields = fields

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, trim_whitespace=True)
