import apps.students.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="resume",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=apps.students.models.student_resume_upload_path,
            ),
        ),
    ]
