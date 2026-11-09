from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.students.validators import validate_pdf_resume

from .models import AlumniProfile, ReferralRequest, ReferralRequestHistory

User = get_user_model()


class AlumniProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AlumniProfile
        fields = [
            "id",
            "username",
            "full_name",
            "email",
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
            "username",
            "full_name",
            "email",
            "verification_status",
            "created_at",
            "updated_at",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def validate_graduation_year(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Graduation year must be greater than zero."
            )
        return value


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

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username


class ReferralRequestHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source="changed_by.username",
        read_only=True,
    )

    class Meta:
        model = ReferralRequestHistory
        fields = [
            "id",
            "event",
            "previous_status",
            "new_status",
            "changed_by_username",
            "note",
            "created_at",
        ]
        read_only_fields = fields


class ReferralRequestSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(
        source="student.username",
        read_only=True,
    )
    student_name = serializers.SerializerMethodField()
    student_department = serializers.SerializerMethodField()
    student_graduation_year = serializers.SerializerMethodField()
    alumni_name = serializers.SerializerMethodField()
    alumni_company = serializers.CharField(
        source="alumni_profile.current_company",
        read_only=True,
    )
    alumni_designation = serializers.CharField(
        source="alumni_profile.designation",
        read_only=True,
    )
    has_resume = serializers.SerializerMethodField()
    history = ReferralRequestHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ReferralRequest
        fields = [
            "id",
            "student_username",
            "student_name",
            "student_department",
            "student_graduation_year",
            "alumni_name",
            "alumni_company",
            "alumni_designation",
            "opportunity_url",
            "note",
            "has_resume",
            "status",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    def get_student_department(self, obj):
        profile = getattr(obj.student, "student_profile", None)
        return profile.department if profile else ""

    def get_student_graduation_year(self, obj):
        profile = getattr(obj.student, "student_profile", None)
        return profile.graduation_year if profile else None

    def get_alumni_name(self, obj):
        user = obj.alumni_profile.user
        return user.get_full_name() or user.username

    def get_has_resume(self, obj):
        return bool(obj.resume and obj.resume.name)


class ReferralRequestCreateSerializer(serializers.Serializer):
    alumni_profile_id = serializers.IntegerField(min_value=1)
    opportunity_url = serializers.URLField(max_length=500)
    resume = serializers.FileField(
        allow_empty_file=False,
        validators=[validate_pdf_resume],
    )
    note = serializers.CharField(max_length=2000, trim_whitespace=True)

    def validate_alumni_profile_id(self, value):
        profile = AlumniProfile.objects.filter(
            pk=value,
            verification_status=AlumniProfile.VerificationStatus.VERIFIED,
            is_open_to_referrals=True,
        ).first()
        if profile is None:
            raise serializers.ValidationError(
                "This alumni profile is unavailable for referral requests."
            )
        self.context["alumni_profile"] = profile
        return value

    def validate_note(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Please provide at least 10 characters about the referral request."
            )
        return value.strip()


class ReferralRequestActionSerializer(serializers.Serializer):
    note = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate_note(self, value):
        return value.strip()
