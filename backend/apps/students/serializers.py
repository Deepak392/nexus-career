from rest_framework import serializers

from .models import StudentProfile
from .validators import validate_pdf_resume


class CleanStringListField(serializers.ListField):
    child = serializers.CharField(
        max_length=100,
        allow_blank=True,
        trim_whitespace=True,
    )

    def to_internal_value(self, data):
        values = super().to_internal_value(data)
        return [value for value in values if value]


class StudentProfileSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    skills = CleanStringListField(required=False, default=list)
    areas_of_interest = CleanStringListField(required=False, default=list)
    preferred_roles = CleanStringListField(required=False, default=list)
    preferred_locations = CleanStringListField(required=False, default=list)
    resume = serializers.FileField(
        write_only=True,
        required=False,
        allow_empty_file=False,
        validators=[validate_pdf_resume],
    )
    remove_resume = serializers.BooleanField(write_only=True, required=False, default=False)
    has_resume = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            "id", "student_id", "department", "degree_programme", "graduation_year",
            "cgpa", "skills", "areas_of_interest", "experience", "preferred_roles",
            "preferred_locations", "work_mode", "resume", "remove_resume",
            "has_resume", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "has_resume", "created_at", "updated_at"]

    def get_has_resume(self, obj):
        return obj.has_resume

    def validate_student_id(self, value):
        return value.strip() or None if value is not None else None

    def validate_graduation_year(self, value):
        if value <= 0:
            raise serializers.ValidationError("Graduation year must be greater than zero.")
        return value

    def validate_cgpa(self, value):
        if value is not None and not 0 <= value <= 10:
            raise serializers.ValidationError("CGPA must be between 0 and 10.")
        return value

    def validate(self, attrs):
        if attrs.get("remove_resume") and attrs.get("resume"):
            raise serializers.ValidationError(
                {"resume": "Upload a replacement or remove the existing resume, not both."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("remove_resume", False)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        remove_resume = validated_data.pop("remove_resume", False)
        replacing_resume = "resume" in validated_data
        old_resume = instance.resume if instance.resume else None
        if remove_resume:
            validated_data["resume"] = None
        updated = super().update(instance, validated_data)
        if old_resume and (remove_resume or replacing_resume):
            old_resume.delete(save=False)
        return updated
