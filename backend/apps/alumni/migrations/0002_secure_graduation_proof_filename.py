import apps.alumni.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alumni", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alumniprofile",
            name="graduation_proof",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=apps.alumni.models.alumni_graduation_proof_upload_path,
            ),
        ),
    ]
