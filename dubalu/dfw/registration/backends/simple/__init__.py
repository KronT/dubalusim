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

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User

from ... import signals
from ...forms import RegistrationForm


class SimpleBackend(object):
    """
    A registration backend which implements the simplest possible
    workflow: a user supplies an email address and password
    (the bare minimum for a useful account), and is immediately signed
    up and logged in.

    """
    def register(self, request, **kwargs):
        """
        Create and immediately log in a new user.

        """
        form_kwargs = {'password': kwargs['password1']}
        for field in set([getattr(User, 'USERNAME_FIELD', 'username')] + list(User.REQUIRED_FIELDS)):
            if field in kwargs:
                form_kwargs[field] = kwargs[field]

        email, password = form_kwargs['email'], form_kwargs['password']
        User.objects.create_user(email, password=password)

        # authenticate() always has to be called before login(), and
        # will return the user we just created.
        new_user = authenticate(email=email, password=password)
        login(request, new_user)
        signals.user_registered.send(sender=self.__class__,
                                     user=new_user,
                                     request=request)
        return new_user

    def activate(self, **kwargs):
        raise NotImplementedError

    def registration_allowed(self, request):
        """
        Indicate whether account registration is currently permitted,
        based on the value of the setting ``REGISTRATION_OPEN``. This
        is determined as follows:

        * If ``REGISTRATION_OPEN`` is not specified in settings, or is
          set to ``True``, registration is permitted.

        * If ``REGISTRATION_OPEN`` is both specified and set to
          ``False``, registration is not permitted.

        """
        return getattr(settings, 'REGISTRATION_OPEN', True)

    def get_form_class(self, request):
        return RegistrationForm

    def post_registration_redirect(self, request, user):
        """
        After registration, redirect to the user's account page.

        """
        return (user.get_absolute_url(), (), {})

    def post_activation_redirect(self, request, user):
        raise NotImplementedError
