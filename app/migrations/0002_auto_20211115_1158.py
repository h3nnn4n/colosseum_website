# Generated by Django 3.2.9 on 2021-11-15 11:58

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="agent",
            name="name",
            field=models.CharField(max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="agent",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="auth.user"
            ),
            preserve_default=False,
        ),
    ]