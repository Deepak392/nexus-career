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

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
