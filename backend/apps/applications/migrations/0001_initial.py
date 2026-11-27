import apps.applications.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("opportunities", "0002_opportunity_eligibility_criteria"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Application",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under review"), ("SHORTLISTED", "Shortlisted"), ("SELECTED", "Selected"), ("REJECTED", "Rejected"), ("WITHDRAWN", "Withdrawn")], default="SUBMITTED", max_length=20)),
                ("resume", models.FileField(upload_to=apps.applications.models.application_resume_upload_path)),
                ("eligibility_snapshot", models.JSONField(default=dict)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("opportunity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="applications", to="opportunities.opportunity")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="career_applications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "applications",
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.CreateModel(
            name="ApplicationStatusHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under review"), ("SHORTLISTED", "Shortlisted"), ("SELECTED", "Selected"), ("REJECTED", "Rejected"), ("WITHDRAWN", "Withdrawn")], max_length=20)),
                ("note", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="status_history", to="applications.application")),
                ("changed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="application_status_changes", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "application_status_history",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="application",
            constraint=models.UniqueConstraint(fields=("student", "opportunity"), name="uniq_student_opportunity_application"),
        ),
        migrations.AddIndex(
            model_name="application",
            index=models.Index(fields=["student", "submitted_at"], name="application_student_date_idx"),
        ),
        migrations.AddIndex(
            model_name="application",
            index=models.Index(fields=["opportunity", "status"], name="application_opp_status_idx"),
        ),
    ]
