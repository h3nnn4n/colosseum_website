# Generated by Django 3.2.9 on 2021-11-19 18:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("app", "0013_agentrating")]

    operations = [
        migrations.AddField(
            model_name="agent", name="draws", field=models.IntegerField(default=0)
        ),
        migrations.AddField(
            model_name="agent",
            name="elo",
            field=models.DecimalField(decimal_places=2, default=1500, max_digits=10),
        ),
        migrations.AddField(
            model_name="agent", name="loses", field=models.IntegerField(default=0)
        ),
        migrations.AddField(
            model_name="agent",
            name="score",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="agent", name="wins", field=models.IntegerField(default=0)
        ),
        migrations.DeleteModel(name="AgentRating"),
    ]