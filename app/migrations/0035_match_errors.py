# Generated by Django 3.2.9 on 2021-11-26 21:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0034_alter_match_tournament")]

    operations = [
        migrations.AddField(
            model_name="match", name="errors", field=models.JSONField(default=dict)
        )
    ]
