# Generated by Django 3.2.9 on 2021-11-22 20:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("app", "0022_agent_active")]

    operations = [migrations.RemoveField(model_name="agent", name="file_path")]
