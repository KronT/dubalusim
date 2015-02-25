# -*- coding: utf-8 -*-
"""
Dubalu Framework: Registration Urls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Backwards-compatible URLconf for existing django-registration
installs; this allows the standard ``include('dfw.registration.urls')`` to
continue working, but that usage is deprecated and will be removed for
django-registration 1.0. For new installs, use
``include('dfw.registration.backends.default.urls')``.

:author: Dubalu Framework Team. See AUTHORS.
:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:copyright: Copyright (c) 2007-2012, James Bennett.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

import warnings

warnings.warn(
    "include('dfw.registration.urls') is deprecated; use include('dfw.registration.backends.default.urls') instead.",
    PendingDeprecationWarning)

from .backends.default.urls import *  # NOQA
