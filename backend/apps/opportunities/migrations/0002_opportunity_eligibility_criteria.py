from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("opportunities", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="eligibility_criteria",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
