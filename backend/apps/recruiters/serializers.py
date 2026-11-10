from rest_framework import serializers

from .models import Company


class CompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "website",
            "industry",
            "contact_email",
            "contact_phone",
            "description",
            "verification_status",
            "verification_rejection_reason",
            "verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "verification_status",
            "verification_rejection_reason",
            "verified_at",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Company name is required.")
        return value

    def validate_industry(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Industry is required.")
        return value


class RejectionReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(
        min_length=5,
        max_length=2000,
        trim_whitespace=True,
    )
