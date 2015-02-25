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

from django.test import TestCase
from django.contrib.auth import get_user_model

from .. import forms


class RegistrationFormTests(TestCase):
    """
    Test the default registration forms.

    """
    def test_registration_form(self):
        """
        Test that ``RegistrationForm`` enforces username constraints
        and matching passwords.

        """
        User = get_user_model()
        # Create a user so we can verify that duplicate usernames aren't
        # permitted.
        User.objects.create_user('alice@example.com', password='secret')

        invalid_data_dicts = [
            # invalid email.
            {'data': {'email': 'foo.example.com',
                      'password1': 'foo',
                      'password2': 'foo'},
             'error': ('email', ["Enter a valid email address."])},
            # Already-existing email.
            {'data': {'email': 'alice@example.com',
                      'password1': 'secret',
                      'password2': 'secret'},
             'error': ('__all__', ["User already registered."])},
            # Mismatched passwords.
            {'data': {'email': 'foo@example.com',
                      'password1': 'foo',
                      'password2': 'bar'},
             'error': ('__all__', ["The two password fields didn't match."])},
        ]

        for invalid_dict in invalid_data_dicts:
            form = forms.RegistrationForm(data=invalid_dict['data'])
            self.failIf(form.is_valid())
            error_name = invalid_dict['error'][0]
            error_description = invalid_dict['error'][1]
            self.assertEqual(form.errors[error_name], error_description)

        form = forms.RegistrationForm(data={'email': 'foo@example.com',
                                            'password1': 'foo',
                                            'password2': 'foo'})
        self.failUnless(form.is_valid())

    def test_registration_form_tos(self):
        """
        Test that ``RegistrationFormTermsOfService`` requires
        agreement to the terms of service.

        """
        form = forms.RegistrationFormTermsOfService(data={'full_name': "Foo Someone",
                                                          'email': 'foo@example.com',
                                                          'password1': 'foo',
                                                          'password2': 'foo'})
        self.failIf(form.is_valid())
        self.assertEqual(form.errors['tos'],
                         ["You must agree to the terms to register"])

        form = forms.RegistrationFormTermsOfService(data={'full_name': "Foo Someone",
                                                          'email': 'foo@example.com',
                                                          'password1': 'foo',
                                                          'password2': 'foo',
                                                          'tos': 'on'})
        self.failUnless(form.is_valid())

    def test_registration_form_unique_email(self):
        """
        Test that ``RegistrationFormUniqueEmail`` validates uniqueness
        of email addresses.

        """
        User = get_user_model()
        # Create a user so we can verify that duplicate addresses
        # aren't permitted.
        User.objects.create_user('alice@example.com', password='secret')

        form = forms.RegistrationFormUniqueEmail(data={'email': 'alice@example.com',
                                                       'password1': 'foo',
                                                       'password2': 'foo'})
        self.failIf(form.is_valid())
        self.assertEqual(form.errors['email'],
                         ["This email address is already in use. Please supply a different email address."])

        form = forms.RegistrationFormUniqueEmail(data={'email': 'foo@example.com',
                                                       'password1': 'foo',
                                                       'password2': 'foo'})
        self.failUnless(form.is_valid())

    def test_registration_form_no_free_email(self):
        """
        Test that ``RegistrationFormNoFreeEmail`` disallows
        registration with free email addresses.

        """
        base_data = {'password1': 'foo',
                     'password2': 'foo'}
        for domain in forms.RegistrationFormNoFreeEmail.bad_domains:
            invalid_data = base_data.copy()
            invalid_data['email'] = "foo@%s" % domain
            form = forms.RegistrationFormNoFreeEmail(data=invalid_data)
            self.failIf(form.is_valid())
            self.assertEqual(form.errors['email'],
                             ["Registration using free email addresses is prohibited. Please supply a different email address."])

        base_data['email'] = 'foo@example.com'
        form = forms.RegistrationFormNoFreeEmail(data=base_data)
        self.failUnless(form.is_valid())
