# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

from ..default import DefaultBackend
from ...forms import RegistrationFormTermsOfService


class TermsOfServiceBackend(DefaultBackend):
    def get_form_class(self, request):
        return RegistrationFormTermsOfService
