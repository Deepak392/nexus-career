import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


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
        upload_to="alumni/graduation_proofs/",
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


def referral_resume_upload_path(instance, filename):
    """Use an opaque server-generated path for private referral resumes."""
    return f"private/alumni-referral-resumes/{uuid.uuid4().hex}.pdf"


class ReferralRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REFERRED = "REFERRED", "Referred"
        DECLINED = "DECLINED", "Declined"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="alumni_referral_requests",
    )
    alumni_profile = models.ForeignKey(
        AlumniProfile,
        on_delete=models.PROTECT,
        related_name="referral_requests",
    )
    opportunity_url = models.URLField(max_length=500)
    resume = models.FileField(upload_to=referral_resume_upload_path)
    note = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alumni_referral_requests"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "alumni_profile", "opportunity_url"],
                condition=Q(status__in=["PENDING", "ACCEPTED"]),
                name="uniq_active_student_alumni_referral",
            ),
        ]
        indexes = [
            models.Index(
                fields=["alumni_profile", "status", "created_at"],
                name="ref_alumni_status_date_idx",
            ),
            models.Index(
                fields=["student", "created_at"],
                name="ref_student_date_idx",
            ),
        ]

    def __str__(self):
        return f"Referral {self.pk}: {self.student.username} -> {self.alumni_profile.user.username}"


class ReferralRequestHistory(models.Model):
    class Event(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        INFORMATION_REQUESTED = "INFORMATION_REQUESTED", "More information requested"
        STUDENT_RESPONSE = "STUDENT_RESPONSE", "Student response"
        REFERRED = "REFERRED", "Referred"

    referral_request = models.ForeignKey(
        ReferralRequest,
        on_delete=models.PROTECT,
        related_name="history",
    )
    event = models.CharField(max_length=32, choices=Event.choices)
    previous_status = models.CharField(
        max_length=20,
        choices=ReferralRequest.Status.choices,
        blank=True,
    )
    new_status = models.CharField(
        max_length=20,
        choices=ReferralRequest.Status.choices,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="alumni_referral_history",
    )
    note = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alumni_referral_request_history"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Referral {self.referral_request_id}: {self.event}"
