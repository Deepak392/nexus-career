from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("STUDENT", "Student"),
                    ("RECRUITER", "Recruiter"),
                    ("IPC_ADMIN", "IPC Administrator"),
                    ("ALUMNI", "Alumni"),
                    ("SYSTEM_ADMIN", "System Administrator"),
                ],
                default="SYSTEM_ADMIN",
                max_length=20,
            ),
        ),
    ]
