# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

from django.utils.text import ugettext_lazy as _

from dfw.sections.base import BaseSection


class RegisterSection(BaseSection):
    class Meta:
        title = _("Sign up")
        reverse = 'registration_register'
        roles = ('anonymous',)


class LoginSection(BaseSection):
    class Meta:
        title = _("Sign in")
        reverse = 'login'
        roles = ('anonymous',)


class LogoutSection(BaseSection):
    class Meta:
        title = _("Sign out")
        reverse = 'logout'
        roles = ('user',)


class AbstractRegistration(BaseSection):
    register = RegisterSection()
    login = LoginSection()
    logout = LogoutSection()

    class Meta:
        abstract = True
        title = _("Registration")
        urls = ['dfw.registration.backends.tos.urls']


class Registration(AbstractRegistration):
    class Meta(AbstractRegistration.Meta):
        swappable = 'REGISTRATION_PLUGGABLE'
