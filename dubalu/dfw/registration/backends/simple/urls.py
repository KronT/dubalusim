# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

URLconf for registration and activation, using django-registration's
one-step backend.

If the default behavior of these views is acceptable to you, simply
use a line like this in your root URLconf to set up the default URLs
for registration::

    (r'^accounts/', include('dfw.registration.backends.simple.urls')),

This will also automatically set up the views in
``django.contrib.auth`` at sensible default locations.

If you'd like to customize the behavior (e.g., by passing extra
arguments to the various views) or split up the URLs, feel free to set
up your own URL patterns for these views instead.

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:copyright: Copyright (c) 2007-2012, James Bennett.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template

from ...views import register


def get_urlpatterns(backend='dfw.registration.backends.simple.SimpleBackend'):
    return patterns('',
        url(
            r'^register/$',
            register,
            {
                'backend': backend,
            },
            name='registration_register',
        ),
        url(
            r'^register/closed/$',
            direct_to_template,
            {
                'template_name': 'registration/registration_closed.html',
                'backend': backend,
            },
            name='registration_disallowed',
        ),
        (r'', include('dfw.registration.auth_urls')),
    )

urlpatterns = get_urlpatterns()
