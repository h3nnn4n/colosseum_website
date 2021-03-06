# Generated by Django 3.2.9 on 2021-11-22 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0017_match_participants")]

    operations = [
        migrations.AddField(
            model_name="tournament",
            name="end_date",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="tournament",
            name="mode",
            field=models.CharField(
                choices=[
                    ("ROUND_ROBIN", "Round Robin"),
                    ("DOUBLE_ROUND_ROBIN", "Double Round Robin"),
                    ("TRIPLE_ROUND_ROBIN", "Triple Round Robin"),
                    ("DAILY", "Daily"),
                ],
                default="ROUND_ROBIN",
                max_length=64,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tournament",
            name="start_date",
            field=models.DateTimeField(null=True),
        ),
    ]
