# Generated by Django 3.2.13 on 2022-05-08 15:58

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0081_userprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="Trophy",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("FIRST", "First Place"),
                            ("SECOND", "Second Place"),
                            ("THIRD", "Third Place"),
                        ],
                        max_length=255,
                    ),
                ),
                (
                    "agent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trophies",
                        to="app.agent",
                    ),
                ),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trophies",
                        to="app.game",
                    ),
                ),
                (
                    "season",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trophies",
                        to="app.season",
                    ),
                ),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trophies",
                        to="app.tournament",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="trophy",
            index=models.Index(fields=["agent"], name="app_trophy_agent_i_3d5804_idx"),
        ),
        migrations.AddIndex(
            model_name="trophy",
            index=models.Index(fields=["game"], name="app_trophy_game_id_346cbf_idx"),
        ),
        migrations.AddIndex(
            model_name="trophy",
            index=models.Index(fields=["season"], name="app_trophy_season__073e4f_idx"),
        ),
        migrations.AddIndex(
            model_name="trophy",
            index=models.Index(
                fields=["tournament"], name="app_trophy_tournam_3a2f0e_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="trophy",
            index=models.Index(fields=["type"], name="app_trophy_type_9a495d_idx"),
        ),
    ]
