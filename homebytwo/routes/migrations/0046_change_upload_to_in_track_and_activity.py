# Generated by Django 2.2.16 on 2020-09-16 18:04
from django.core import management
from django.db import migrations

import homebytwo.routes.fields
import homebytwo.routes.models.activity
import homebytwo.routes.models.track
from homebytwo.routes.management.commands import cleanup_hdf5_files


def move_files(apps, schema_editor):
    Route = apps.get_model("routes", "Route")
    Activity = apps.get_model("routes", "Activity")

    for route in Route.objects.all():
        if route.data is not None:
            del route.data.filepath
            route.save(update_fields=["data"])

    for activity in Activity.objects.all():
        if activity.streams is not None:
            del activity.streams.filepath
            activity.save(update_fields=["streams"])

    management.call_command(cleanup_hdf5_files.Command())


class Migration(migrations.Migration):

    dependencies = [
        ("routes", "0045_make_activity_performance-timestamped"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activity",
            name="streams",
            field=homebytwo.routes.fields.DataFrameField(
                null=True,
                unique_fields=["strava_id"],
                upload_to=homebytwo.routes.models.activity.athlete_streams_directory_path,
            ),
        ),
        migrations.AlterField(
            model_name="route",
            name="data",
            field=homebytwo.routes.fields.DataFrameField(
                null=True,
                unique_fields=["uuid"],
                upload_to=homebytwo.routes.models.track.athlete_data_directory_path,
            ),
        ),
        migrations.RunPython(move_files, move_files),
    ]