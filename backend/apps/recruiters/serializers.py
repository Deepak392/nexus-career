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


class AdminDashboardMetricsSerializer(serializers.Serializer):
    active_opportunities = serializers.IntegerField(
        help_text="Number of published opportunities currently open for applications."
    )
    students = serializers.IntegerField(
        help_text="Total number of active student accounts."
    )
    verified_recruiters = serializers.IntegerField(
        help_text="Number of verified companies or recruiters."
    )
    applications = serializers.IntegerField(
        help_text="Total number of student applications submitted."
    )
    pending_approvals = serializers.IntegerField(
        help_text="Number of opportunities awaiting IPC approval."
    )
    total_opportunities = serializers.IntegerField(
        required=False,
        help_text="Total number of all opportunities across all lifecycle states."
    )
    pending_companies = serializers.IntegerField(
        required=False,
        help_text="Number of companies pending IPC verification."
    )
    verified_alumni = serializers.IntegerField(
        required=False,
        help_text="Number of verified alumni profiles."
    )


class ActivityReportItemSerializer(serializers.Serializer):
    """R6: Serializer for an individual recruitment activity report record."""

    id = serializers.CharField(help_text="Unique event or activity identifier.")
    timestamp = serializers.DateTimeField(help_text="UTC timestamp of the activity.")
    activity_type = serializers.CharField(help_text="Category of activity (e.g. OPPORTUNITY, APPLICATION, COMPANY, USER).")
    action = serializers.CharField(help_text="Action descriptor (e.g. OPPORTUNITY_APPROVED, APPLICATION_SUBMITTED).")
    actor = serializers.CharField(help_text="Username of the user who performed the activity.")
    company = serializers.CharField(allow_blank=True, default="", help_text="Associated company name.")
    target_type = serializers.CharField(help_text="Target entity model or type.")
    target_id = serializers.CharField(help_text="Identifier of the target entity.")
    status = serializers.CharField(allow_blank=True, default="", help_text="Status outcome of the activity.")
    details = serializers.DictField(default=dict, help_text="Contextual metadata or details.")


class ActivityReportFilterParamsSerializer(serializers.Serializer):
    """R6: Filter parameters for administrative activity reports and CSV exports."""

    start_date = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Filter activities from this ISO 8601 date (inclusive, e.g. YYYY-MM-DD)."
    )
    end_date = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Filter activities up to this ISO 8601 date (inclusive, e.g. YYYY-MM-DD)."
    )
    activity_type = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Filter by activity category (e.g. OPPORTUNITY, APPLICATION, COMPANY, USER)."
    )
    company = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Filter by company name (substring match) or numeric company ID."
    )
    status = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Filter by status (e.g. PUBLISHED, SUBMITTED, VERIFIED, REJECTED, SUSPENDED)."
    )

