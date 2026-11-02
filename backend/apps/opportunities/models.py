from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Opportunity(models.Model):

    class OpportunityType(models.TextChoices):
        JOB = "JOB", "Job"
        INTERNSHIP = "INTERNSHIP", "Internship"

    class WorkMode(models.TextChoices):
        ONSITE = "ONSITE", "On-site"
        HYBRID = "HYBRID", "Hybrid"
        REMOTE = "REMOTE", "Remote"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
        PUBLISHED = "PUBLISHED", "Published"
        REJECTED = "REJECTED", "Rejected"
        CLOSED = "CLOSED", "Closed"
        ARCHIVED = "ARCHIVED", "Archived"

    company = models.ForeignKey(
        "recruiters.Company",
        on_delete=models.PROTECT,
        related_name="opportunities",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_opportunities",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_opportunities",
    )

    title = models.CharField(max_length=200)
    description = models.TextField()

    opportunity_type = models.CharField(
        max_length=20,
        choices=OpportunityType.choices,
    )

    required_skills = models.JSONField(default=list, blank=True)

    work_mode = models.CharField(
        max_length=10,
        choices=WorkMode.choices,
    )

    location = models.CharField(max_length=200)

    compensation = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    application_deadline = models.DateTimeField()

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    application_method = models.CharField(
        max_length=20,
        choices=[
            ("PLATFORM", "Platform"),
            ("EXTERNAL", "External Link"),
        ],
        default="PLATFORM",
    )

    external_application_url = models.URLField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "opportunities"
        indexes = [
            models.Index(
                fields=["status", "application_deadline"],
                name="opp_status_deadline_idx",
            ),
            models.Index(
                fields=["company"],
                name="opp_company_idx",
            ),
            models.Index(
                fields=["opportunity_type"],
                name="opp_type_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(compensation__gte=0) | Q(compensation__isnull=True),
                name="opp_compensation_nonnegative",
            ),
        ]

    @property
    def is_open(self):
        return (
            self.status == self.Status.PUBLISHED
            and self.application_deadline > timezone.now()
        )

    def __str__(self):
        return f"{self.title} - {self.company.name}"
