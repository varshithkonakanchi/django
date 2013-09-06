# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.db.models.loading import BaseAppCache
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class UnicodeModel(models.Model):
    title = models.CharField('ÚÑÍ¢ÓÐÉ', max_length=20, default='“Ðjáñgó”')

    class Meta:
        # Disable auto loading of this model as we load it on our own
        app_cache = BaseAppCache()
        verbose_name = 'úñí©óðé µóðéø'
        verbose_name_plural = 'úñí©óðé µóðéøß'

    def __str__(self):
        return self.title
