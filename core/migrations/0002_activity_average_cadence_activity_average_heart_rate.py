# Generated by Django 5.1.4 on 2025-03-22 23:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='average_cadence',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='activity',
            name='average_heart_rate',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
