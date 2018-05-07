# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-02-10 07:22
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityPerformance',
            fields=[
                ('id', models.AutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID')),
                ('vam_up', models.FloatField(default=400)),
                ('vam_down', models.FloatField(default=2000)),
                ('flat_pace', models.FloatField(default=4000)),
            ],
        ),
        migrations.CreateModel(
            name='ActivityType',
            fields=[
                ('id', models.AutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('default_vam_up', models.FloatField(default=400)),
                ('default_vam_down', models.FloatField(default=2000)),
                ('default_flat_pace', models.FloatField(default=4000)),
            ],
        ),
        migrations.CreateModel(
            name='Athlete',
            fields=[
                ('id', models.AutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID')),
                ('strava_token', models.CharField(max_length=100, null=True)),
                ('switzerland_mobility_cookie', models.CharField(max_length=100, null=True)),
                ('activies', models.ManyToManyField(
                    through='routes.ActivityPerformance',
                    to='routes.ActivityType')),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Place',
            fields=[
                ('id', models.AutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID')),
                ('place_type', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=250, verbose_name='Name of the place')),
                ('description', models.TextField(
                    default='',
                    verbose_name='Text description of the Place')),
                ('altitude', models.FloatField(null=True)),
                ('public_transport', models.BooleanField(default=False)),
                ('data_source', models.CharField(
                    default='homebytwo',
                    max_length=50,
                    verbose_name='Where the place came from')),
                ('source_id', models.CharField(
                    max_length=50,
                    verbose_name='Place ID at the data source')),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                    verbose_name='Time of creation')),
                ('updated_at', models.DateTimeField(
                    auto_now=True,
                    verbose_name='Time of last update')),
                ('geom', django.contrib.gis.db.models.fields.PointField(srid=21781)),
            ],
        ),
        migrations.CreateModel(
            name='RoutePlace',
            fields=[
                ('id', models.AutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID')),
                ('line_location', models.FloatField(default=0)),
                ('altitude_on_route', models.FloatField()),
                ('place', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='routes.Place')),
            ],
        ),
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.AutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(
                    default='',
                    verbose_name='Textual description')),
                ('totalup', models.FloatField(
                    default=0,
                    verbose_name='Total elevation gain in m')),
                ('totaldown', models.FloatField(
                    default=0,
                    verbose_name='Total elevation loss in m')),
                ('length', models.FloatField(
                    default=0,
                    verbose_name='Total length of the track in m')),
                ('updated', models.DateTimeField(
                    auto_now=True,
                    verbose_name='Time of last update')),
                ('created', models.DateTimeField(
                    auto_now_add=True,
                    verbose_name='Time of creation')),
                ('geom', django.contrib.gis.db.models.fields.LineStringField(
                    srid=21781,
                    verbose_name='line geometry')),
                ('source_id', models.BigIntegerField()),
                ('data_source', models.CharField(
                    default='homebytwo',
                    max_length=50,
                    verbose_name='Where the route came from')),
                ('end_place', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ends_route',
                    to='routes.Place')),
                ('places', models.ManyToManyField(
                    blank=True,
                    through='routes.RoutePlace',
                    to='routes.Place')),
                ('start_place', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='starts_route',
                    to='routes.Place')),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Segment',
            fields=[
                ('id', models.AutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID')),
                ('name', models.CharField(
                    default='',
                    max_length=100)),
                ('elevation_up', models.FloatField(
                    default=0,
                    verbose_name='elevation gain in m')),
                ('elevation_down', models.FloatField(
                    default=0,
                    verbose_name='elevation loss in m')),
                ('geom', django.contrib.gis.db.models.fields.LineStringField(
                    srid=21781,
                    verbose_name='line geometry')),
                ('end_place', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='ends',
                    to='routes.Place')),
                ('start_place', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='starts',
                    to='routes.Place')),
            ],
        ),
        migrations.AddField(
            model_name='routeplace',
            name='route',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='routes.Route'),
        ),
        migrations.AlterUniqueTogether(
            name='place',
            unique_together=set([('data_source', 'source_id')]),
        ),
        migrations.AddField(
            model_name='activityperformance',
            name='activity_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='routes.ActivityType'),
        ),
        migrations.AddField(
            model_name='activityperformance',
            name='athlete',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='routes.Athlete'),
        ),
        migrations.AlterUniqueTogether(
            name='route',
            unique_together=set([('user', 'data_source', 'source_id')]),
        ),
    ]
