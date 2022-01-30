# Generated by Django 3.2.11 on 2022-01-30 13:25

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("app", "0079_match_raw_result"),
    ]

    operations = [
        migrations.AlterField(
            model_name="agent",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="agents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]