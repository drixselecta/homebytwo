# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-14 20:23
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracks', '0002_auto_20160614_2221'),
    ]

    operations = [
        migrations.AlterField(
            model_name='swissplaces',
            name='geom',
            field=django.contrib.gis.db.models.fields.MultiPointField(srid=21781),
        ),
    ]
