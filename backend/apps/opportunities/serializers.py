from rest_framework import serializers

from .models import Opportunity


class OpportunitySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            "id",
            "title",
            "description",
            "company_name",
            "opportunity_type",
            "required_skills",
            "work_mode",
            "location",
            "compensation",
            "application_deadline",
            "start_date",
            "application_method",
            "external_application_url",
            "status",
            "published_at",
            "created_at",
        ]
        read_only_fields = fields
