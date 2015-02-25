# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

A management command which deletes expired accounts (e.g.,
accounts which signed up but never activated) from the database.

Calls ``RegistrationProfile.objects.delete_expired_users()``, which
contains the actual logic for determining which accounts are deleted.

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:copyright: Copyright (c) 2007-2012, James Bennett.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

from django.core.management.base import NoArgsCommand

from ...models import RegistrationProfile


class Command(NoArgsCommand):
    help = "Delete expired user registrations from the database"

    def handle_noargs(self, **options):
        RegistrationProfile.objects.delete_expired_users()
