# Generated by Django 3.2.9 on 2021-11-16 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0006_agent_files")]

    operations = [
        migrations.RemoveField(model_name="agent", name="files"),
        migrations.AddField(
            model_name="agent",
            name="file_path",
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
    ]
