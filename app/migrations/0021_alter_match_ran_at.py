# Generated by Django 3.2.9 on 2021-11-22 16:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0020_alter_tournament_mode")]

    operations = [
        migrations.AlterField(
            model_name="match", name="ran_at", field=models.DateTimeField(null=True)
        )
    ]
