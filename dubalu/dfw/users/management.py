# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

Creates the default Site object.

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from django.conf import settings
from django.db.models import signals
from django.db import connections
from django.db import router
from django.core.management.color import no_style

from dfw.entities.models import Entity

from django.contrib.auth import get_user_model
User = get_user_model()

user_app = __import__(User.__module__, fromlist=[''])


def create_default_anonymous_user(app, created_models, verbosity, db, **kwargs):
    # Only create the default sites in databases where Django created the table
    if User in created_models and router.allow_syncdb(db, User):
        if verbosity >= 2:
            print("Creating anonymous User object")

        user = User(
            pk=settings.ANONYMOUS_USER_ID,
            username='AnonymousUser',
            first_name='Anonymous',
            last_name='User',
        )

        user.is_setup = True  # prevent default profiles to be created, because the sequence hasn't been updated
        user.save(using=db)

        # We set an explicit pk instead of relying on auto-incrementation,
        # so we need to reset the database sequence. See #17415.
        sequence_sql = connections[db].ops.sequence_reset_sql(no_style(), [User])
        if not sequence_sql:
            sequence_sql = connections[db].ops.sequence_reset_sql(no_style(), [Entity])
        if sequence_sql:
            if verbosity >= 2:
                print("Resetting sequence")
            cursor = connections[db].cursor()
            for command in sequence_sql:
                cursor.execute(command)

        user.is_setup = False  # allow default profiles to be created now
        user.save(using=db)

signals.post_syncdb.connect(create_default_anonymous_user, sender=user_app)
