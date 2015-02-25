# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""


def sync(verbosity=1):
    from django.conf import settings
    from dfw.permissions.models import create_rule_permission

    # For the rules to be active, we *must* register them (use manage.py's syncrules command):
    for i, rule in enumerate(settings.ENTITIES_RULES):
        create_rule_permission(*rule, ordering=i, verbosity=verbosity)
