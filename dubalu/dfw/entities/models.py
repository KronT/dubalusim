# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals
from django.db import models
from django.conf import settings

from uuidfield.fields import UUIDField
from uuidfield.utils import encode_uuid
from autoconnect.decorators import autoconnect

from dfw.core.plugins.models.statable import AbstractStatableModel, StatableManager


class EntityManager(StatableManager):
    pass


class AbstractEntity(AbstractStatableModel):
    id = UUIDField(primary_key=True)

    owner = models.ForeignKey(settings.CORE_USER_MODEL, null=True, editable=False)

    objects = EntityManager()

    class Meta:
        abstract = True

    def unified(self):
        return self.is_unified

    @property
    def is_unified(self):
        return not bool(self.owner_id) or self.owner_id == self.id

    def get_owner(self):
        if self.is_unified:
            return self
        return self.owner

    @property
    def eid(self):
        return self.id and encode_uuid(self.id)

    @property
    def entity_ueid(self):
        """
        Ex.: entity_type := 'U101'
        """
        try:
            entity_type = self.etype
        except TypeError:
            entity_type = ''
        if self.eid:
            return '%s~%s' % (entity_type, self.eid)
        return entity_type

    def pre_save(self):
        if not self.id:
            self.id = self._meta.get_field('id').create_uuid()
        if not self.owner_id:
            # Initialize an owner (or self)
            self.owner = self


@autoconnect
class Entity(AbstractEntity):
    class Meta(AbstractEntity.Meta):
        swappable = 'CORE_ENTITY_MODEL'
