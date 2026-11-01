from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_profile",
    )

    student_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )

    department = models.CharField(max_length=100)

    degree_programme = models.CharField(max_length=100)

    graduation_year = models.PositiveIntegerField()

    cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10),
        ],
    )

    skills = models.JSONField(default=list, blank=True)

    areas_of_interest = models.JSONField(default=list, blank=True)

    experience = models.TextField(blank=True)

    preferred_roles = models.JSONField(default=list, blank=True)

    preferred_locations = models.JSONField(default=list, blank=True)

    work_mode = models.CharField(
        max_length=20,
        choices=[
            ("ONSITE", "On-site"),
            ("HYBRID", "Hybrid"),
            ("REMOTE", "Remote"),
        ],
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student_profiles"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(cgpa__gte=0, cgpa__lte=10)
                    | models.Q(cgpa__isnull=True)
                ),
                name="student_cgpa_valid_range",
            ),
        ]

    def __str__(self):
        return f"Student Profile: {self.user.username}"
