# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '__latest__'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action_time', models.DateTimeField(auto_now=True, verbose_name='action time')),
                ('object_id', models.TextField(null=True, verbose_name='object id', blank=True)),
                ('object_repr', models.CharField(max_length=200, verbose_name='object repr')),
                ('action_flag', models.PositiveSmallIntegerField(verbose_name='action flag')),
                ('change_message', models.TextField(verbose_name='change message', blank=True)),
                ('content_type', models.ForeignKey(to_field='id', blank=True, to='contenttypes.ContentType', null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, to_field='id')),
            ],
            options={
                'ordering': ('-action_time',),
                'db_table': 'django_admin_log',
                'verbose_name': 'log entry',
                'verbose_name_plural': 'log entries',
            },
            bases=(models.Model,),
        ),
    ]
