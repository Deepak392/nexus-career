from rest_framework import serializers

from .models import Application, ApplicationStatusHistory


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source="changed_by.username",
        read_only=True,
    )

    class Meta:
        model = ApplicationStatusHistory
        fields = ["status", "note", "changed_by_username", "created_at"]
        read_only_fields = fields


class ApplicationSerializer(serializers.ModelSerializer):
    opportunity_id = serializers.IntegerField(source="opportunity.id", read_only=True)
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True)
    company_name = serializers.CharField(source="opportunity.company.name", read_only=True)
    opportunity_type = serializers.CharField(
        source="opportunity.opportunity_type",
        read_only=True,
    )
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "opportunity_id",
            "opportunity_title",
            "company_name",
            "opportunity_type",
            "status",
            "eligibility_snapshot",
            "submitted_at",
            "updated_at",
            "status_history",
        ]
        read_only_fields = fields


class ApplicationSubmissionSerializer(serializers.Serializer):
    opportunity_id = serializers.IntegerField(min_value=1)


class ApplicationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Application.Status.choices)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class RecruiterApplicationSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    student_username = serializers.CharField(source="student.username", read_only=True)
    student_email = serializers.EmailField(source="student.email", read_only=True)
    opportunity_id = serializers.IntegerField(source="opportunity.id", read_only=True)
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True)
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)
    has_resume = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id",
            "student_id",
            "student_username",
            "student_email",
            "opportunity_id",
            "opportunity_title",
            "status",
            "has_resume",
            "eligibility_snapshot",
            "submitted_at",
            "updated_at",
            "status_history",
        ]
        read_only_fields = fields

    def get_has_resume(self, obj) -> bool:
        return bool(obj.resume)

