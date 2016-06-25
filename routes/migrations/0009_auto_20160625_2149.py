# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-25 19:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0008_auto_20160623_2242'),
    ]

    operations = [
        migrations.RenameField(
            model_name='place',
            old_name='place_type',
            new_name='type',
        ),
        migrations.AddField(
            model_name='place',
            name='language',
            field=models.CharField(default='de', max_length=50),
            preserve_default=False,
        ),
    ]
