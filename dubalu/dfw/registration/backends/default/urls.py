# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

URLconf for registration and activation, using django-registration's
default backend.

If the default behavior of these views is acceptable to you, simply
use a line like this in your root URLconf to set up the default URLs
for registration::

    (r'^accounts/', include('dfw.registration.backends.default.urls')),

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

from ...views import activate, register, direct_to_template


def get_urlpatterns(backend='dfw.registration.backends.default.DefaultBackend'):
    return patterns('',
        url(
            r'^activate/complete/$',
            direct_to_template,
            {
                'template_name': 'registration/activate.html',
                'backend': backend,
                'extra_context': {'account': True},
            },
            name='registration_activation_complete',
        ),
        # Activation keys get matched by \w+ instead of the more specific
        # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
        # that way it can return a sensible "invalid key" message instead of a
        # confusing 404.
        url(
            r'^activate/(?P<activation_key>\w+)/$',
            activate,
            {
                'backend': backend,
            },
            name='registration_activate',
        ),
        url(
            r'^register/$',
            register,
            {
                'backend': backend,
            },
            name='registration_register',
        ),
        url(
            r'^register/complete/$',
            direct_to_template,
            {
                'template_name': 'registration/registration_complete.html',
                'backend': backend,
            },
            name='registration_complete'),
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
