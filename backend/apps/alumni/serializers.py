from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import AlumniProfile


class AlumniProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = AlumniProfile

        fields = [
            "id",
            "department",
            "degree_programme",
            "graduation_year",
            "current_company",
            "designation",
            "industry",
            "is_open_to_referrals",
            "verification_status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "verification_status",
            "created_at",
            "updated_at",
        ]


class AlumniSearchSerializer(serializers.ModelSerializer):

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = AlumniProfile
        fields = [
            "id",
            "full_name",
            "department",
            "degree_programme",
            "graduation_year",
            "current_company",
            "designation",
            "industry",
            "is_open_to_referrals",
        ]

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username

    def validate_graduation_year(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Graduation year must be greater than zero."
            )
        return value


class AlumniVerificationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[AlumniProfile.VerificationStatus.VERIFIED, AlumniProfile.VerificationStatus.REJECTED],
        required=True,
        help_text="Verification decision: VERIFIED or REJECTED.",
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Mandatory explanation if status is REJECTED.",
    )

    def validate(self, attrs):
        status_val = attrs.get("status")
        reason = attrs.get("rejection_reason", "").strip()

        if status_val == AlumniProfile.VerificationStatus.REJECTED and not reason:
            raise serializers.ValidationError(
                {"rejection_reason": "A rejection reason is required when rejecting an alumnus profile."}
            )

        attrs["rejection_reason"] = reason
        return attrs


class AlumniVerificationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Identifier of the alumni profile.")
    user_id = serializers.IntegerField(help_text="User ID of the alumnus.")
    username = serializers.CharField(help_text="Username of the alumnus.")
    verification_status = serializers.CharField(help_text="Updated verification status.")
    department = serializers.CharField(help_text="Department.")
    degree_programme = serializers.CharField(help_text="Degree programme.")
    graduation_year = serializers.IntegerField(help_text="Graduation year.")
    graduation_proof = serializers.CharField(allow_null=True, required=False, help_text="Evidence document URL or path.")
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    updated_at = serializers.DateTimeField(help_text="Timestamp of update.")
