# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from django.conf import settings


def core(request):
    context = {
        'PROJECT_NAME': settings.PROJECT_NAME,
        'PROJECT_SUFFIX': settings.PROJECT_SUFFIX,
    }
    return context
