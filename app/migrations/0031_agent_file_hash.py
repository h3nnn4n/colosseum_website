# Generated by Django 3.2.9 on 2021-11-25 16:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0030_tournament_automated_number")]

    operations = [
        migrations.AddField(
            model_name="agent",
            name="file_hash",
            field=models.CharField(max_length=128, null=True, unique=True),
        )
    ]
