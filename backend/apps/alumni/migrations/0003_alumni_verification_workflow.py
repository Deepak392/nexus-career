import django.db.models.deletion
import apps.alumni.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("alumni", "0002_referral_workflows"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="alumniprofile",
            name="graduation_proof",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=apps.alumni.models.graduation_proof_upload_path,
            ),
        ),
        migrations.AddField(
            model_name="alumniprofile",
            name="verification_rejection_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="alumniprofile",
            name="verified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="verified_alumni_profiles",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="alumniprofile",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="alumniprofile",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reviewed_alumni_profiles",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="alumniprofile",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
