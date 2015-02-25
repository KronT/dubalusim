# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:copyright: Copyright (c) 2007-2012, James Bennett.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

VERSION = (0, 8, 0, 'final', 0)


def get_version():
    from django.utils.version import get_version
    return get_version(VERSION)
