# Generated by Django 2.2.13 on 2020-07-02 08:00

import django.contrib.postgres.fields
from django.db import migrations, models

import homebytwo.routes.fields
import homebytwo.routes.models.activity


class Migration(migrations.Migration):

    dependencies = [
        ("routes", "0041_activity_streams"),
    ]

    operations = [
        migrations.RenameField(
            model_name="activity", old_name="totalup", new_name="total_elevation_gain",
        ),
        migrations.RemoveField(model_name="activityperformance", name="flat_param",),
        migrations.RemoveField(model_name="activityperformance", name="slope_param",),
        migrations.RemoveField(
            model_name="activityperformance", name="slope_squared_param",
        ),
        migrations.RemoveField(
            model_name="activityperformance", name="total_elevation_gain_param",
        ),
        migrations.RemoveField(model_name="activitytype", name="flat_param",),
        migrations.RemoveField(model_name="activitytype", name="slope_param",),
        migrations.RemoveField(model_name="activitytype", name="slope_squared_param",),
        migrations.RemoveField(
            model_name="activitytype", name="total_elevation_gain_param",
        ),
        migrations.AddField(
            model_name="activity",
            name="commute",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="activityperformance",
            name="cv_scores",
            field=homebytwo.routes.fields.NumpyArrayField(
                base_field=models.FloatField(),
                default=homebytwo.routes.models.activity.get_default_array,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="activityperformance",
            name="flat_parameter",
            field=models.FloatField(default=0.36),
        ),
        migrations.AddField(
            model_name="activityperformance",
            name="model_score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="activityperformance",
            name="regression_coefficients",
            field=homebytwo.routes.fields.NumpyArrayField(
                base_field=models.FloatField(),
                default=homebytwo.routes.models.activity.get_default_array,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="activityperformance",
            name="gear_categories",
            field=homebytwo.routes.fields.NumpyArrayField(
                base_field=models.CharField(max_length=50),
                default=homebytwo.routes.models.activity.get_default_category,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="activityperformance",
            name="workout_type_categories",
            field=homebytwo.routes.fields.NumpyArrayField(
                base_field=models.CharField(max_length=50),
                default=homebytwo.routes.models.activity.get_default_category,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="activitytype",
            name="gear_categories",
            field=homebytwo.routes.fields.NumpyArrayField(
                base_field=models.CharField(max_length=50),
                default=homebytwo.routes.models.activity.get_default_category,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="activitytype",
            name="workout_type_categories",
            field=homebytwo.routes.fields.NumpyArrayField(
                base_field=models.CharField(max_length=50),
                default=homebytwo.routes.models.activity.get_default_category,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="activitytype",
            name="flat_parameter",
            field=models.FloatField(default=0.36),
        ),
        migrations.AddField(
            model_name="activitytype",
            name="max_gradient",
            field=models.FloatField(default=100.0),
        ),
        migrations.AddField(
            model_name="activitytype",
            name="max_pace",
            field=models.FloatField(default=2.4),
        ),
        migrations.AddField(
            model_name="activitytype",
            name="min_gradient",
            field=models.FloatField(default=-100.0),
        ),
        migrations.AddField(
            model_name="activitytype",
            name="min_pace",
            field=models.FloatField(default=0.12),
        ),
        migrations.AddField(
            model_name="activitytype",
            name="regression_coefficients",
            field=homebytwo.routes.fields.NumpyArrayField(
                base_field=models.FloatField(),
                default=homebytwo.routes.models.activity.get_default_array,
                size=None,
            ),
        ),
    ]
