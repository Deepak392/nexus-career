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
    verification_rejection_reason = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="verified_companies",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_companies",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies"
        indexes = [
            models.Index(fields=["name"], name="companies_name_idx"),
            models.Index(fields=["verification_status"], name="companies_verify_idx"),
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
            models.Index(fields=["company"], name="recruiter_company_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.company.name}"


class WorkflowAuditEvent(models.Model):
    class ObjectType(models.TextChoices):
        COMPANY = "COMPANY", "Company"
        OPPORTUNITY = "OPPORTUNITY", "Opportunity"
        USER = "USER", "User"
        ALUMNI = "ALUMNI", "Alumni"

    class Action(models.TextChoices):
        COMPANY_CREATED = "COMPANY_CREATED", "Company created"
        COMPANY_PROFILE_UPDATED = "COMPANY_PROFILE_UPDATED", "Company profile updated"
        COMPANY_VERIFIED = "COMPANY_VERIFIED", "Company verified"
        COMPANY_REJECTED = "COMPANY_REJECTED", "Company rejected"
        OPPORTUNITY_SUBMITTED = "OPPORTUNITY_SUBMITTED", "Opportunity submitted"
        OPPORTUNITY_APPROVED = "OPPORTUNITY_APPROVED", "Opportunity approved"
        OPPORTUNITY_REJECTED = "OPPORTUNITY_REJECTED", "Opportunity rejected"
        OPPORTUNITY_CLOSED = "OPPORTUNITY_CLOSED", "Opportunity closed"
        OPPORTUNITY_ARCHIVED = "OPPORTUNITY_ARCHIVED", "Opportunity archived"
        USER_SUSPENDED = "USER_SUSPENDED", "User suspended"
        USER_REACTIVATED = "USER_REACTIVATED", "User reactivated"
        ALUMNI_VERIFIED = "ALUMNI_VERIFIED", "Alumni verified"
        ALUMNI_REJECTED = "ALUMNI_REJECTED", "Alumni rejected"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="workflow_audit_events",
    )
    object_type = models.CharField(max_length=20, choices=ObjectType.choices)
    object_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=40, choices=Action.choices)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_audit_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["object_type", "object_id", "created_at"],
                name="workflow_obj_created_idx",
            ),
            models.Index(
                fields=["actor", "created_at"],
                name="workflow_actor_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.action} ({self.object_type}:{self.object_id})"
