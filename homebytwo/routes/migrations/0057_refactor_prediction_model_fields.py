# Generated by Django 2.2.17 on 2020-11-17 20:44

from django.db import migrations, models
import django.db.models.deletion
import homebytwo.routes.fields
import homebytwo.routes.models.activity


class Migration(migrations.Migration):

    dependencies = [
        ("routes", "0056_activity_performance_related_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="activitytype",
            name="gear_categories",
        ),
        migrations.AddField(
            model_name="activitytype",
            name="cv_scores",
            field=homebytwo.routes.fields.NumpyArrayField(
                base_field=models.FloatField(),
                default=homebytwo.routes.models.activity.get_default_array,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="activitytype",
            name="model_score",
            field=models.FloatField(default=0.0),
        ),
    ]