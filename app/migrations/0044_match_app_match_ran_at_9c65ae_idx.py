# Generated by Django 3.2.9 on 2021-12-08 12:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0043_alter_agent_game")]

    operations = [
        migrations.AddIndex(
            model_name="match",
            index=models.Index(
                fields=["ran_at", "data", "id"], name="app_match_ran_at_9c65ae_idx"
            ),
        )
    ]
