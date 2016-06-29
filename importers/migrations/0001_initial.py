# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-29 12:33
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SwitzerlandMobilityRoute',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('totalup', models.FloatField(default=0, verbose_name='Total elevation difference up in m')),
                ('totaldown', models.FloatField(default=0, verbose_name='Total elevation difference down in m')),
                ('length', models.FloatField(default=0, verbose_name='Total length of the track in m')),
                ('description', models.TextField(default='', verbose_name='Text description of the Route')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Time of last update')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Time of last creation')),
                ('geom', django.contrib.gis.db.models.fields.LineStringField(srid=21781, verbose_name='line geometry')),
                ('switzerland_mobility_id', models.BigIntegerField(unique=True)),
            ],
        ),
    ]
