from rest_framework import serializers

from .models import Company, RecruiterProfile


class RecruiterVerificationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[Company.VerificationStatus.VERIFIED, Company.VerificationStatus.REJECTED],
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

        if status_val == Company.VerificationStatus.REJECTED and not reason:
            raise serializers.ValidationError(
                {"rejection_reason": "A rejection reason is required when rejecting a company/recruiter."}
            )

        attrs["rejection_reason"] = reason
        return attrs


class RecruiterVerificationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Identifier of the recruiter profile.")
    recruiter_username = serializers.CharField(help_text="Username of the recruiter.")
    company_id = serializers.IntegerField(help_text="Identifier of the associated company.")
    company_name = serializers.CharField(help_text="Name of the company.")
    verification_status = serializers.CharField(help_text="Updated verification status.")
    verified_by = serializers.IntegerField(help_text="User ID of the IPC administrator who verified.")
    verified_at = serializers.DateTimeField(help_text="Timestamp when verification occurred.")
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
