import apps.accounts.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_role_default"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="user",
            managers=[
                ("objects", apps.accounts.models.UserManager()),
            ],
        ),
    ]
