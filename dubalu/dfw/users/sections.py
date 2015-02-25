# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from django.utils.text import ugettext_lazy as _

from dfw.pluggables.base import pluggable
from dfw.sections.base import BaseSection


@pluggable('users')
class AbstractUsers(BaseSection):
    class Meta:
        abstract = True
        title = _("Users")
        # urls = ['dfw.users.urls']


class Users(AbstractUsers):
    class Meta(AbstractUsers.Meta):
        swappable = 'USERS_PLUGGABLE'
