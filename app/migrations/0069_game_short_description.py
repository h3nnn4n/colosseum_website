# Generated by Django 3.2.10 on 2021-12-29 17:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0068_game_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="short_description",
            field=models.TextField(default=""),
        ),
    ]