# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

Forms and validation code for user registration.

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:copyright: Copyright (c) 2007-2012, James Bennett.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

import warnings

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import authenticate
from django.core import urlresolvers
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites import get_current_site
from django.contrib.auth import get_user_model


# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary. If/when Django ticket #3515
# lands in trunk, this will no longer be necessary.
attrs_dict = {'class': 'required'}


class AuthenticationForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """

    error_messages = {
        'invalid_login': _("Please enter a correct %(username)s and password. "
                           "Note that both fields may be case-sensitive."),
        'inactive': _("This account is inactive."),
    }

    def __init__(self, request=None, *args, **kwargs):
        """
        The 'request' parameter is set for custom auth use by subclasses.
        The form data comes in via the standard 'data' kwarg.
        """
        self.request = request
        self.user_cache = None
        super(AuthenticationForm, self).__init__(*args, **kwargs)

        # Set the label for the "username" field.
        UserModel = get_user_model()
        self.username_field_name = getattr(UserModel, 'USERNAME_FIELD', 'username')
        self.username_field = UserModel._meta.get_field(
            self.username_field_name)
        self.fields[self.username_field_name] = UserModel._meta.get_field(
            self.username_field_name).formfield()
        self.fields['password'] = forms.CharField(
            label=_("Password"), widget=forms.PasswordInput)

    def clean(self):
        password = self.cleaned_data.get('password')

        # Normalized username:
        username = self.cleaned_data.get(self.username_field_name)
        if username and password:
            UserModel = get_user_model()

            username = UserModel.objects.normalize_email(username)
            self.cleaned_data[self.username_field_name] = username

            self.user_cache = authenticate(username=username,
                                           password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            elif not self.user_cache.is_active:
                raise forms.ValidationError(
                    self.error_messages['inactive'],
                    code='inactive',
                )
        return self.cleaned_data

    def check_for_test_cookie(self):
        warnings.warn("check_for_test_cookie is deprecated; ensure your login "
                      "view is CSRF-protected.", DeprecationWarning)

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


class AuthenticationRememberMeForm(AuthenticationForm):
    remember_me = forms.BooleanField(label=_("Remember Me"), initial=True,
        required=False)


class RegistrationForm(forms.Form):
    """
    Form for registering a new user account.

    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend.
    """

    def __init__(self, *args, **kwargs):
        UserModel = get_user_model()
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.username_field_name = getattr(UserModel, 'USERNAME_FIELD', 'username')
        self.fields[self.username_field_name] = UserModel._meta.get_field(
            self.username_field_name).formfield()

        self.fields[
            'password1'] = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                           label=_("New Password"))
        self.fields[
            'password2'] = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                           label=_("Password (again)"))

        for field in UserModel.REQUIRED_FIELDS:
            self.fields[field] = UserModel._meta.get_field(field).formfield()

    def clean(self):
        """
        Verifiy that the values entered into the two password fields match and
        validate that the username is alphanumeric and is not already in use.
        Note that an error here will end up in ``non_field_errors()`` because
        it doesn't apply to a single
        field.
        """
        # Normalized username:
        username = self.cleaned_data.get(self.username_field_name)

        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_(
                    "The two password fields didn't match."))

        if username:
            UserModel = get_user_model()

            username = UserModel.objects.normalize_email(username)
            self.cleaned_data[self.username_field_name] = username

            existing = UserModel.objects.filter(**{
                self.username_field_name + '__iexact': username,
                'is_active': True,
            })
            if existing.exists():
                raise forms.ValidationError(_("User already registered."))
        return self.cleaned_data


def tos():
    if not hasattr(tos, '_tos'):
        terms_url = None
        for url in ('terms', 'tos', 'section:terms', 'section:tos'):
            try:
                terms_url = urlresolvers.reverse(url)
            except urlresolvers.NoReverseMatch:
                pass
        if terms_url is None:
            tos._tos = _(u'I have read and agree to the Terms of Service')
        else:
            tos._tos = _(u'I have read and agree to the <a href="%(terms_url)s" target="_blank">Terms of Service</a>') % dict(terms_url=terms_url)
    return tos._tos


class RegistrationFormTermsOfService(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which adds a required checkbox
    for agreeing to a site's Terms of Service.

    """
    full_name = forms.CharField(label=_("Full Name"))
    tos = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=tos,
                             error_messages={'required': _("You must agree to the terms to register")})


class RegistrationFormUniqueEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which enforces uniqueness of
    email addresses.

    """
    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.

        """
        UserModel = get_user_model()
        if UserModel.objects.filter(
            email__iexact=self.cleaned_data['email'],
            is_active=True,
        ):
            raise forms.ValidationError(_(
                "This email address is already in use. Please supply a different email address."))
        return self.cleaned_data['email']


class RegistrationFormNoFreeEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which disallows registration with
    email addresses from popular free webmail services; moderately
    useful for preventing automated spam registrations.

    To change the list of banned domains, subclass this form and
    override the attribute ``bad_domains``.

    """
    bad_domains = ['aim.com', 'aol.com', 'email.com', 'gmail.com',
                   'googlemail.com', 'hotmail.com', 'hushmail.com',
                   'msn.com', 'mail.ru', 'mailinator.com', 'live.com',
                   'yahoo.com']

    def clean_email(self):
        """
        Check the supplied email address against a list of known free
        webmail domains.

        """
        email_domain = self.cleaned_data['email'].split('@')[1]
        if email_domain in self.bad_domains:
            raise forms.ValidationError(
                _("Registration using free email addresses is prohibited. Please supply a different email address."))
        return self.cleaned_data['email']


class PasswordResetForm(forms.Form):
    email = forms.EmailField(label=_("Email"), max_length=254)

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None):
        """
        Generates a one-use only link for resetting password and sends to the
        user.

        """
        UserModel = get_user_model()
        email = self.cleaned_data["email"]
        active_users = UserModel._default_manager.filter(
            email__iexact=email, is_active=True)

        PROTOCOL = 'https' if use_https else 'http'
        if not domain_override:
            current_site = get_current_site(request)
            SITE_NAME = current_site.name
            SITE_DOMAIN = current_site.domain
        else:
            SITE_NAME = SITE_DOMAIN = domain_override

        for user in active_users:
            # Do allow senfing of emails to a users that actually have a password
            # marked as unusable. (differs from django's PasswordResetForm)

            # create_notice_body(
            #     'registration.password_reset',
            #     user,
            #     uid=urlsafe_base64_encode(force_bytes(user.pk)),
            #     token=token_generator.make_token(user),
            #     PROTOCOL=PROTOCOL,
            #     SITE_NAME=SITE_NAME,
            #     SITE_DOMAIN=SITE_DOMAIN,
            # ).post_to(user)
            pass
