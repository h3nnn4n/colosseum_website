# Generated by Django 3.2.9 on 2021-11-24 20:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("app", "0028_alter_tournament_automated")]

    operations = [
        migrations.RenameField(
            model_name="tournament", old_name="automated", new_name="is_automated"
        )
    ]
