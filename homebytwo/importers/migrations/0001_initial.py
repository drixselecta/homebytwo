# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-02-10 07:22
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('routes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StravaRoute',
            fields=[
                ('route_ptr', models.OneToOneField(
                    auto_created=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    serialize=False,
                    to='routes.Route')),
                ('strava_route_id', models.BigIntegerField(unique=True)),
                ('type', models.CharField(max_length=1)),
                ('sub_type', models.CharField(max_length=1)),
                ('strava_timestamp', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
            bases=('routes.route',),
        ),
        migrations.CreateModel(
            name='Swissname3dPlace',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('routes.place',),
        ),
        migrations.CreateModel(
            name='SwitzerlandMobilityRoute',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('routes.route',),
        ),
    ]
