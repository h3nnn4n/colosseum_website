# Generated by Django 3.2.10 on 2022-01-03 14:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0075_match_end_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="outcome",
            field=models.JSONField(default=dict),
        ),
    ]
