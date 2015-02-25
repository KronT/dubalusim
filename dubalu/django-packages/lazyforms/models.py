# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.db import models

from cachedlabel import CachedLabelManagerMixinFactory
from django_extensions.db.fields import CreationDateTimeField


class LazyFormsManager(models.Manager, CachedLabelManagerMixinFactory(label_name='hash')):
    pass


class LazyForms(models.Model):
    form_class = models.CharField(max_length=200)
    field_name = models.CharField(max_length=100, null=True)
    helper = models.CharField(max_length=100)

    created_at = CreationDateTimeField(db_index=True)

    objects = LazyFormsManager()

    @property
    def hash(self):
        return hash((self.form_class, self.field_name, self.helper))

    class Meta:
        unique_together = ('form_class', 'field_name', 'helper')
