
from rest_framework import serializers

from .models import StudentProfile


class StudentProfileSerializer(serializers.ModelSerializer):

    skills = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        allow_empty=True,
    )

    areas_of_interest = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        allow_empty=True,
    )

    preferred_roles = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        allow_empty=True,
    )

    preferred_locations = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        allow_empty=True,
    )

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "student_id",
            "department",
            "degree_programme",
            "graduation_year",
            "cgpa",
            "skills",
            "areas_of_interest",
            "experience",
            "preferred_roles",
            "preferred_locations",
            "work_mode",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_graduation_year(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Graduation year must be greater than zero."
            )
        return value

    def validate_cgpa(self, value):
        if value is not None and not 0 <= value <= 10:
            raise serializers.ValidationError(
                "CGPA must be between 0 and 10."
            )
        return value
