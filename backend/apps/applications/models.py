import uuid

from django.conf import settings
from django.db import models


def application_resume_upload_path(instance, filename):
    """Assign every submitted resume a generated private storage name."""
    return f"private/application-resumes/{uuid.uuid4().hex}.pdf"


class Application(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        SELECTED = "SELECTED", "Selected"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="career_applications",
    )
    opportunity = models.ForeignKey(
        "opportunities.Opportunity",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    resume = models.FileField(upload_to=application_resume_upload_path)
    eligibility_snapshot = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "applications"
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "opportunity"],
                name="uniq_student_opportunity_application",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "submitted_at"], name="application_student_date_idx"),
            models.Index(fields=["opportunity", "status"], name="application_opp_status_idx"),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.opportunity.title}"


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.PROTECT,
        related_name="status_history",
    )
    status = models.CharField(max_length=20, choices=Application.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="application_status_changes",
    )
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "application_status_history"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.application_id}: {self.status}"
