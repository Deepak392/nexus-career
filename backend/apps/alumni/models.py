import uuid

from django.conf import settings
from django.db import models


def alumni_graduation_proof_upload_path(instance, filename):
    """Store proof documents under generated names, not client filenames."""
    return f"alumni/graduation_proofs/{uuid.uuid4().hex}.pdf"


class AlumniProfile(models.Model):

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="alumni_profile",
    )

    department = models.CharField(max_length=100)
    degree_programme = models.CharField(max_length=100)
    graduation_year = models.PositiveIntegerField()

    current_company = models.CharField(max_length=150, blank=True)
    designation = models.CharField(max_length=150, blank=True)
    industry = models.CharField(max_length=100, blank=True)

    is_open_to_referrals = models.BooleanField(default=False)

    graduation_proof = models.FileField(
        upload_to=alumni_graduation_proof_upload_path,
        null=True,
        blank=True,
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alumni_profiles"

    def __str__(self):
        return f"Alumni Profile: {self.user.username}"
