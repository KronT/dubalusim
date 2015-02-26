# -*- coding: utf-8 -*-
"""
Dubalu Framework: CFDI Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals, print_function

from django.conf import settings
from django.conf.urls import patterns, url


urlpatterns = patterns('sample.mysampleapp.views',
    url(r'^$', 'item_list', name='item-list'),
    url(r'^add/$', 'item_create', name='item-add'),
    # url(r'^detail/(?P<pk>' + settings.ENTITY_PK_PATTERN + ')/$', 'client_detail', name='client-detail'),
    # url(r'^edit/(?P<pk>' + settings.ENTITY_PK_PATTERN + ')/$', 'client_update', name='client-edit'),
    # url(r'^delete/(?P<pk>' + settings.ENTITY_PK_PATTERN + ')/$', 'client_delete', name='client-delete'),
    # url(r'^undelete/(?P<pk>' + settings.ENTITY_PK_PATTERN + ')/$', 'client_undelete', name='client-undelete'),
)
