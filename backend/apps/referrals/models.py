from django.conf import settings
from django.db import models


class Referral(models.Model):

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        SUBMITTED = "SUBMITTED", "Submitted"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_referrals",
    )

    alumni = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_referrals",
    )

    opportunity = models.ForeignKey(
        "opportunities.Opportunity",
        on_delete=models.PROTECT,
        related_name="referrals",
    )

    message = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "referrals"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "alumni", "opportunity"],
                name="unique_student_alumni_opportunity_referral",
            ),
        ]

    def __str__(self):
        return (
            f"{self.student.username} → "
            f"{self.alumni.username}: {self.opportunity.title}"
        )
        
class ReferralStatusHistory(models.Model):

    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    previous_status = models.CharField(
        max_length=20,
        choices=Referral.Status.choices,
        null=True,
        blank=True,
    )

    new_status = models.CharField(
        max_length=20,
        choices=Referral.Status.choices,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="referral_status_changes",
    )

    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "referral_status_history"
        ordering = ["created_at"]

    def __str__(self):
        return (
            f"Referral {self.referral_id}: "
            f"{self.previous_status} → {self.new_status}"
        )