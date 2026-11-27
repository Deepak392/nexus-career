import django.db.models.deletion
import apps.alumni.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("alumni", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReferralRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("opportunity_url", models.URLField(max_length=500)),
                ("resume", models.FileField(upload_to=apps.alumni.models.referral_resume_upload_path)),
                ("note", models.TextField(max_length=2000)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("REFERRED", "Referred"), ("DECLINED", "Declined")], default="PENDING", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("alumni_profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="referral_requests", to="alumni.alumniprofile")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alumni_referral_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "alumni_referral_requests",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ReferralRequestHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event", models.CharField(choices=[("REQUESTED", "Requested"), ("ACCEPTED", "Accepted"), ("DECLINED", "Declined"), ("INFORMATION_REQUESTED", "More information requested"), ("STUDENT_RESPONSE", "Student response"), ("REFERRED", "Referred")], max_length=32)),
                ("previous_status", models.CharField(blank=True, choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("REFERRED", "Referred"), ("DECLINED", "Declined")], max_length=20)),
                ("new_status", models.CharField(choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("REFERRED", "Referred"), ("DECLINED", "Declined")], max_length=20)),
                ("note", models.CharField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("changed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alumni_referral_history", to=settings.AUTH_USER_MODEL)),
                ("referral_request", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="history", to="alumni.referralrequest")),
            ],
            options={
                "db_table": "alumni_referral_request_history",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="referralrequest",
            constraint=models.UniqueConstraint(condition=models.Q(("status__in", ["PENDING", "ACCEPTED"])), fields=("student", "alumni_profile", "opportunity_url"), name="uniq_active_student_alumni_referral"),
        ),
        migrations.AddIndex(
            model_name="referralrequest",
            index=models.Index(fields=["alumni_profile", "status", "created_at"], name="ref_alumni_status_date_idx"),
        ),
        migrations.AddIndex(
            model_name="referralrequest",
            index=models.Index(fields=["student", "created_at"], name="ref_student_date_idx"),
        ),
    ]
