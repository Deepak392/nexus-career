import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("alumni", "0002_referral_workflows"),
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("APPLICATION_SUBMITTED", "Application submitted"),
                    ("REFERRAL_REQUEST", "New referral request"),
                    ("REFERRAL_STATUS", "Referral request update"),
                    ("REFERRAL_MORE_INFO", "More information requested"),
                    ("ALUMNI_VERIFICATION", "Alumni verification update"),
                ],
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="referral_request",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="notifications",
                to="alumni.referralrequest",
            ),
        ),
    ]
