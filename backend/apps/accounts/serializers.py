import os
from datetime import date

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from apps.alumni.models import AlumniProfile

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=[
            (User.Role.STUDENT, "Student"),
            (User.Role.ALUMNI, "Alumni"),
            (User.Role.RECRUITER, "Recruiter"),
        ],
        required=True,
    )
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        trim_whitespace=False,
    )
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
    )
    department = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    degree_programme = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    graduation_year = serializers.IntegerField(
        required=False,
        min_value=1900,
        max_value=date.today().year,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "role",
            "department",
            "degree_programme",
            "graduation_year",
        ]
        read_only_fields = ["id"]

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError(
                "An account with this email address already exists."
            )
        return normalized_email

    def validate(self, attrs):
        role = attrs["role"]
        email = attrs.get("email", "")
        email_domain = email.rpartition("@")[2]

        if role == User.Role.STUDENT:
            allowed_domain = os.getenv(
                "STUDENT_EMAIL_DOMAIN",
                "scds.saiuniversity.edu.in",
            ).strip().lower().lstrip("@")
            if email_domain != allowed_domain:
                raise serializers.ValidationError(
                    {
                        "email": (
                            "Student registration requires an authorized "
                            "university email address ending in "
                            f"@{allowed_domain}."
                        )
                    }
                )

        if role == User.Role.ALUMNI:
            required_fields = [
                "department",
                "degree_programme",
                "graduation_year",
            ]
            missing_fields = [
                field for field in required_fields
                if not attrs.get(field)
            ]
            if missing_fields:
                raise serializers.ValidationError(
                    {
                        field: "This field is required for alumni registration."
                        for field in missing_fields
                    }
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data.pop("role")
        alumni_data = {
            "department": validated_data.pop("department", ""),
            "degree_programme": validated_data.pop("degree_programme", ""),
            "graduation_year": validated_data.pop("graduation_year", None),
        }

        user = User.objects.create_user(
            **validated_data,
            role=role,
        )

        if role == User.Role.ALUMNI:
            AlumniProfile.objects.create(
                user=user,
                **alumni_data,
                verification_status=AlumniProfile.VerificationStatus.PENDING,
            )

        return user


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


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
