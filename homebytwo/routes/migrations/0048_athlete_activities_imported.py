# Generated by Django 2.2.16 on 2020-10-01 16:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0047_add_skip_field_and_remove_manual_field_on_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='athlete',
            name='activities_imported',
            field=models.BooleanField(default=False),
        ),
    ]