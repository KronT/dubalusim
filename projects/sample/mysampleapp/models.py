# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals  # >> important to ease the migration to python3

from django.db import models
from django.utils.translation import ugettext_lazy as _


GENDER_MALE = 'M'  # >> single quotes for internal strings
GENDER_FEMALE = 'F'
GENDER_CHOICES = (
    (GENDER_MALE, _("Male")),  # >> double quotes for strings displayed to users (translation enabled with ugettext_lazy or ugettext)
    (GENDER_FEMALE, _("Female")),
)


class MySampleManager(models.Manager):
    pass


class MySampleModel(models.Model):
    name = models.CharField(max_length=50)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    age = models.PositiveIntegerField(null=True, blank=True)
