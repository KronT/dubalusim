# -*- coding: utf-8 -*-
"""
Dubalu Framework: CFDI Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals, print_function

from django.conf.urls import patterns, url, include


urlpatterns = patterns('',
    url(r'^myapp/', include('sample.mysampleapp.urls')),
)
