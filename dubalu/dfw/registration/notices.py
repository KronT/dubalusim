# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals, print_function


def sync(verbosity=1):
    from django.conf import settings

    from dfw.notification.models import create_notice_type

    create_notice_type(
        'registration.activation',
        "Send an activation email",
        "Sends activation email to registered users.",
        medium_labels=[settings.MEDIUM_EMAIL],
        options={
            'templates-email-subject': ['registration/activation_email_subject.txt'],
            'templates-email-body-text': ['registration/activation_email.txt'],
            'templates-email-body-html': ['registration/activation_email.html'],
        },
        immediate=True,
        verbosity=verbosity,
    )

    create_notice_type(
        'registration.password_reset',
        "Send a password reset email",
        "Sends password reset email to registered users.",
        medium_labels=[settings.MEDIUM_EMAIL],
        options={
            'templates-email-subject': ['registration/password_reset_email_subject.txt'],
            'templates-email-body-text': ['registration/password_reset_email.txt'],
            'templates-email-body-html': ['registration/password_reset_email.html'],
        },
        immediate=True,
        verbosity=verbosity,
    )
