# Generated by Django 3.2.9 on 2021-11-24 20:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0025_match_replay")]

    operations = [
        migrations.AddField(
            model_name="tournament", name="automated", field=models.NullBooleanField()
        )
    ]
