# Generated by Django 3.2.13 on 2022-05-09 01:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0083_auto_20220508_2217"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="trophy",
            unique_together={("agent", "tournament")},
        ),
        migrations.AddIndex(
            model_name="trophy",
            index=models.Index(
                fields=["agent", "tournament"], name="app_trophy_agent_i_b7d7a9_idx"
            ),
        ),
    ]
