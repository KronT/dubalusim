# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from django.utils.functional import SimpleLazyObject
from django.contrib.contenttypes.models import ContentType

from dehydration import hydrate, DehydratedModel


SESSION_ENTITY = '_entities_entity_id'
SESSION_ENTITY_CTYPE = '_entities_ctype'


def set_entity(request, entity):
    from dfw.profiles.middleware import SESSION_PROFILE, SESSION_PROFILE_CTYPE
    if entity:
        entity = entity.get_owner()
        request.session[SESSION_ENTITY] = entity.id
        request.session[SESSION_ENTITY_CTYPE] = entity.get_polymorphic_ctype().id
        if request.profile and request.profile.owner_id != entity.id:
            request.set_profile(None)
        if (
            request.session.get(SESSION_ENTITY) == request.session.get(SESSION_PROFILE) and
            request.session.get(SESSION_ENTITY_CTYPE) == request.session.get(SESSION_PROFILE_CTYPE)
        ):
            if SESSION_PROFILE in request.session:
                del request.session[SESSION_PROFILE]
            if SESSION_PROFILE_CTYPE in request.session:
                del request.session[SESSION_PROFILE_CTYPE]
    else:
        del request.session[SESSION_ENTITY]
        del request.session[SESSION_ENTITY_CTYPE]
    request.entity = request._cached_entity = entity
    return request._cached_entity


def get_entity(request):
    if getattr(request, '_cached_entity', None) is None:
        entity = None
        entity_id = request.session.get(SESSION_ENTITY)
        if entity_id and SESSION_ENTITY_CTYPE in request.session:
            ctype_id = request.session[SESSION_ENTITY_CTYPE]
            ctype = ContentType.objects.get_for_id(ctype_id)
            modelclass = ctype.model_class()
            entity = hydrate(DehydratedModel(modelclass=modelclass, pk=entity_id))  # raise_exc=False ?
        if entity is None:
            entity = request.user
            if entity.is_anonymous():
                entity = None
        request._cached_entity = entity
    return request._cached_entity


class EntityMiddleware(object):
    def process_request(self, request):
        assert hasattr(request, 'session'), "The Entity middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."

        request.entity = SimpleLazyObject(lambda: get_entity(request))
        request.set_entity = lambda v: set_entity(request, v)
