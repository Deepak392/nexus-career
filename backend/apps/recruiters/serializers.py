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


class RecruiterVerificationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["VERIFIED", "REJECTED"],
        error_messages={"invalid_choice": "Status must be either 'VERIFIED' or 'REJECTED'."},
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        if attrs.get("status") == "REJECTED" and not attrs.get("rejection_reason"):
            raise serializers.ValidationError(
                {"rejection_reason": "A valid rejection reason is required when rejecting a recruiter/company."}
            )
        return attrs


class RecruiterVerificationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    recruiter_username = serializers.CharField(allow_blank=True)
    company_id = serializers.IntegerField()
    company_name = serializers.CharField()
    verification_status = serializers.CharField()
    verified_by = serializers.IntegerField(allow_null=True)
    verified_at = serializers.DateTimeField(allow_null=True)
    rejection_reason = serializers.CharField(allow_blank=True)


class UserSuspensionSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        trim_whitespace=True,
    )


class UserAccountActionResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()
    is_verified = serializers.BooleanField()
    action = serializers.CharField()
    performed_by = serializers.IntegerField(allow_null=True)
    timestamp = serializers.DateTimeField()
    reason = serializers.CharField(allow_blank=True)


class AuditLogActorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField()


class AuditLogEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    actor = AuditLogActorSerializer()
    action = serializers.CharField()
    target_type = serializers.CharField()
    target_id = serializers.IntegerField()
    target = serializers.CharField()
    details = serializers.DictField()
    created_at = serializers.DateTimeField()
