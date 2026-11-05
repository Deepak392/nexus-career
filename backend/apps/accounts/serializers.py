
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
        allowed_domains = ("@scds.saiuniversity.edu.in", "@gmail.com")

        if not any(normalized_email.endswith(domain) for domain in allowed_domains):
            raise serializers.ValidationError(
                "Student registration requires an email address "
                "ending with @scds.saiuniversity.edu.in or @gmail.com"
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
