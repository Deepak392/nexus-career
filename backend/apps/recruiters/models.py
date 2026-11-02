from django.conf import settings
from django.db import models


class Company(models.Model):

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="verified_companies",
    )

    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies"
        indexes = [
            models.Index(
                fields=["name"],
                name="companies_name_idx",
            ),
            models.Index(
                fields=["verification_status"],
                name="companies_verify_idx",
            ),
        ]

    def __str__(self):
        return self.name


class RecruiterProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recruiter_profile",
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="recruiters",
    )

    designation = models.CharField(max_length=100, blank=True)
    work_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recruiter_profiles"
        indexes = [
            models.Index(
                fields=["company"],
                name="recruiter_company_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.company.name}"
