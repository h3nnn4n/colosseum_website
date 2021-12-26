# Generated by Django 3.2.10 on 2021-12-26 20:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0065_alter_agentratings_season")]

    operations = [
        migrations.AlterField(
            model_name="match",
            name="game",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="matches",
                to="app.game",
            ),
        ),
        migrations.AlterField(
            model_name="match",
            name="season",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="matches",
                to="app.season",
            ),
        ),
    ]
