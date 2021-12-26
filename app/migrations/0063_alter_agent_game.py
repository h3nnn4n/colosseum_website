# Generated by Django 3.2.10 on 2021-12-26 13:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0062_auto_20211224_1926")]

    operations = [
        migrations.AlterField(
            model_name="agent",
            name="game",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="agents",
                to="app.game",
            ),
        )
    ]
