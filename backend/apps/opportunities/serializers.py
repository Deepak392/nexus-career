from django.utils import timezone
from rest_framework import serializers

from .models import Opportunity


class OpportunitySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = Opportunity
        fields = [
            "id", "title", "description", "company_name", "created_by_username",
            "opportunity_type", "required_skills", "eligibility_criteria",
            "work_mode", "location", "compensation", "application_deadline",
            "start_date", "application_method", "external_application_url",
            "status", "published_at", "approved_at", "rejection_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class RecruiterOpportunitySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )
    required_skills = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        allow_empty=True,
        required=False,
    )
    eligibility_criteria = serializers.JSONField(required=False)

    class Meta:
        model = Opportunity
        fields = [
            "id", "title", "description", "company_name", "created_by_username",
            "opportunity_type", "required_skills", "eligibility_criteria",
            "work_mode", "location", "compensation", "application_deadline",
            "start_date", "application_method", "external_application_url",
            "status", "published_at", "approved_at", "rejection_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "company_name", "created_by_username", "status",
            "published_at", "approved_at", "rejection_reason",
            "created_at", "updated_at",
        ]

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Opportunity title is required.")
        return value

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 20:
            raise serializers.ValidationError(
                "Description must contain at least 20 characters."
            )
        return value

    def validate_location(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Location is required.")
        return value

    def validate_required_skills(self, value):
        return [skill.strip() for skill in value if skill.strip()]

    def validate_eligibility_criteria(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Eligibility criteria must be a JSON object."
            )
        allowed = {
            "minimum_cgpa", "graduation_years", "degree_programmes",
            "departments", "required_skills",
        }
        unknown = set(value) - allowed
        if unknown:
            raise serializers.ValidationError(
                f"Unsupported eligibility criteria: {', '.join(sorted(unknown))}."
            )
        normalized = dict(value)
        if "minimum_cgpa" in normalized:
            cgpa = normalized["minimum_cgpa"]
            if isinstance(cgpa, bool) or not isinstance(cgpa, (int, float)) or not 0 <= cgpa <= 10:
                raise serializers.ValidationError(
                    "minimum_cgpa must be a number between 0 and 10."
                )
        for field in ("graduation_years", "degree_programmes", "departments", "required_skills"):
            if field not in normalized:
                continue
            values = normalized[field]
            if not isinstance(values, list):
                raise serializers.ValidationError(f"{field} must be a list.")
            if field == "graduation_years":
                invalid = any(
                    isinstance(year, bool) or not isinstance(year, int) or year <= 0
                    for year in values
                )
                if invalid:
                    raise serializers.ValidationError(
                        "graduation_years must contain positive integer years."
                    )
            else:
                if any(not isinstance(item, str) or not item.strip() for item in values):
                    raise serializers.ValidationError(
                        f"{field} must contain non-empty strings."
                    )
                normalized[field] = [item.strip() for item in values]
        return normalized

    def validate_compensation(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Compensation cannot be negative.")
        return value

    def validate_application_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                "Application deadline must be in the future."
            )
        return value

    def validate(self, attrs):
        method = attrs.get(
            "application_method",
            getattr(self.instance, "application_method", "PLATFORM"),
        )
        external_url = attrs.get(
            "external_application_url",
            getattr(self.instance, "external_application_url", ""),
        )
        if method == "EXTERNAL" and not external_url:
            raise serializers.ValidationError({
                "external_application_url": "An external application URL is required."
            })
        if method == "PLATFORM" and external_url:
            raise serializers.ValidationError({
                "external_application_url": "Do not provide an external URL for platform applications."
            })
        return attrs
