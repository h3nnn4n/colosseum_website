# Generated by Django 3.2.9 on 2021-12-07 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0037_tournament_done")]

    operations = [
        migrations.AddIndex(
            model_name="tournament",
            index=models.Index(fields=["done"], name="app_tournam_done_1831dc_idx"),
        )
    ]
