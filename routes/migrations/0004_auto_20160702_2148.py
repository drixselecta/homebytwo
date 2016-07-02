# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-02 19:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0003_auto_20160702_2105'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitytype',
            name='default_flat_pace',
            field=models.FloatField(default=4000),
        ),
        migrations.AddField(
            model_name='activitytype',
            name='default_vam_down',
            field=models.FloatField(default=2000),
        ),
        migrations.AddField(
            model_name='activitytype',
            name='default_vam_up',
            field=models.FloatField(default=400),
        ),
        migrations.AddField(
            model_name='route',
            name='segments',
            field=models.ManyToManyField(to='routes.Segment'),
        ),
        migrations.AddField(
            model_name='segment',
            name='name',
            field=models.CharField(default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='segment',
            name='end_place',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ends', to='routes.Place'),
        ),
        migrations.AlterField(
            model_name='segment',
            name='start_place',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='starts', to='routes.Place'),
        ),
    ]