# -*- coding: utf-8 -*-
from django.db import models

from cachedlabel import CachedLabelManagerMixinFactory


class UUIDNodesManager(models.Manager, CachedLabelManagerMixinFactory(label_name='node')):
    pass


class UUIDNodes(models.Model):
    node = models.BigIntegerField(editable=False, unique=True)

    objects = UUIDNodesManager()
