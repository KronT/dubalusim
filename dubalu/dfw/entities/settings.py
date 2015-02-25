# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

import re

_ = lambda s: s

CORE_ENTITY_MODEL = 'entities.Entity'

ENTITY_PK_PATTERN = r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'
ENTITY_RE = re.compile(r'[EPCO]([a-zA-Z0-9_]{0,9})\.([a-zA-Z0-9_-]{14,24}|ANONYMOUS)')
ANONYMOUS_USER_ID = '00000000-0000-0000-0000-000000000000'

ENTITY_USER = '{USER_PROFILE}'

ENTITY_CHOICES = (
    (ENTITY_USER, _("User")),
)
