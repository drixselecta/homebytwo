# Generated by Django 2.2.17 on 2020-11-19 09:04

from django.db import migrations
from numpy import array


def change_default_coefficients(apps, schema_editor):
    ActivityType = apps.get_model("routes", "ActivityType")
    ActivityType.objects.filter(activities=None).update(
        regression_coefficients=array([0.0, 0.0, 0.075, 0.0004, 0.0001, 0.0001])
    )


def restore_default_coefficients(apps, schema_editor):
    ActivityType = apps.get_model("routes", "ActivityType")
    ActivityType.objects.filter(activities=None).update(
        regression_coefficients=array([0.0, 0.0, 0.0, 0.075, 0.0004, 0.0001, 0.0001])
    )


def train_activity_types_prediction_models(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("routes", "0059_change_min_pace_default_on_activity_type"),
    ]

    operations = [
        migrations.RunPython(change_default_coefficients, restore_default_coefficients),
        migrations.RunPython(
            train_activity_types_prediction_models, migrations.RunPython.noop
        ),
    ]
