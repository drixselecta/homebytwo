# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-03-03 11:39
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0002_route_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='segment',
            name='end_place',
        ),
        migrations.RemoveField(
            model_name='segment',
            name='start_place',
        ),
        migrations.DeleteModel(
            name='Segment',
        ),
    ]
