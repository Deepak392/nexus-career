import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_user_managers"),
        ("recruiters", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="verification_rejection_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="company",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="company",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reviewed_companies",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="WorkflowAuditEvent",
            fields=[
                ("id", models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name="ID",
                )),
                ("object_type", models.CharField(
                    choices=[("COMPANY", "Company"), ("OPPORTUNITY", "Opportunity")],
                    max_length=20,
                )),
                ("object_id", models.PositiveBigIntegerField()),
                ("action", models.CharField(
                    choices=[
                        ("COMPANY_CREATED", "Company created"),
                        ("COMPANY_PROFILE_UPDATED", "Company profile updated"),
                        ("COMPANY_VERIFIED", "Company verified"),
                        ("COMPANY_REJECTED", "Company rejected"),
                        ("OPPORTUNITY_SUBMITTED", "Opportunity submitted"),
                        ("OPPORTUNITY_APPROVED", "Opportunity approved"),
                        ("OPPORTUNITY_REJECTED", "Opportunity rejected"),
                        ("OPPORTUNITY_CLOSED", "Opportunity closed"),
                        ("OPPORTUNITY_ARCHIVED", "Opportunity archived"),
                    ],
                    max_length=40,
                )),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="workflow_audit_events",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": "workflow_audit_events",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["object_type", "object_id", "created_at"],
                        name="workflow_obj_created_idx",
                    ),
                    models.Index(
                        fields=["actor", "created_at"],
                        name="workflow_actor_created_idx",
                    ),
                ],
            },
        ),
    ]
