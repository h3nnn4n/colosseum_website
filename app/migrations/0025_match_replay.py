# Generated by Django 3.2.9 on 2021-11-24 17:09

from django.db import migrations, models

import app.utils


class Migration(migrations.Migration):

    dependencies = [("app", "0024_auto_20211124_1650")]

    operations = [
        migrations.AddField(
            model_name="match",
            name="replay",
            field=models.FileField(null=True, upload_to=app.utils.replay_filepath),
        )
    ]
