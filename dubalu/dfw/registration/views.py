# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

Views which allow users to create and activate accounts.

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:copyright: Copyright (c) 2007-2012, James Bennett.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth import login as auth_login
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import is_safe_url, urlsafe_base64_encode
from django.shortcuts import resolve_url
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.sites import get_current_site

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User

from .forms import AuthenticationRememberMeForm
from .backends import get_backend
from . import signals


def direct_to_template(request, backend,
                       template_name=None,
                       extra_context=None, **kwargs):
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value
    return render_to_response(template_name,
                              kwargs,
                              context_instance=context)


@sensitive_post_parameters()
@csrf_protect
@never_cache
def remember_me_login(request, template_name='registration/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationRememberMeForm,
          current_app=None, extra_context=None):
    """
    Based on login view cribbed from
    https://github.com/django/django/blob/1.6/django/contrib/auth/views.py#L25

    Displays the login form with a remember me checkbox and handles the
    login action.

    The authentication_form parameter has been changed from
    ``django.contrib.auth.forms.AuthenticationForm`` to
    ``remember_me.forms.AuthenticationRememberMeForm``.  To change this, pass a
    different form class as the ``authentication_form`` parameter.

    """

    redirect_to = request.REQUEST.get(redirect_field_name, '')

    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)

            # Okay, security checks complete. Log the user in.
            auth_login(request, form.get_user())

            return HttpResponseRedirect(redirect_to)

        # TODO:
        # Temporary patch to redirect invalid credentials to Yezdo's old app
        elif request.POST.get('email') and request.POST.get('password'):
            from cfdi.views import get_login_redirect
            if not User.objects.filter(email=request.POST.get('email')).exists():
                return get_login_redirect(request.POST['email'], request.POST['password'], url='https://app.yezdo.com/cuentas/ingresar/')

    else:
        form = authentication_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)


def activate(request, backend,
             template_name='registration/activate.html',
             success_url=None, extra_context=None,
             is_admin_site=False,
             token_generator=default_token_generator,
             **kwargs):
    """
    Activate a user's account.

    The actual activation of the account will be delegated to the
    backend specified by the ``backend`` keyword argument (see below);
    the backend's ``activate()`` method will be called, passing any
    keyword arguments captured from the URL, and will be assumed to
    return a ``User`` if activation was successful, or a value which
    evaluates to ``False`` in boolean context if not.

    Upon successful activation, the backend's
    ``post_activation_redirect()`` method will be called, passing the
    ``HttpRequest`` and the activated ``User`` to determine the URL to
    redirect the user to. To override this, pass the argument
    ``success_url`` (see below).

    On unsuccessful activation, will render the template
    ``registration/activate.html`` to display an error message; to
    override thise, pass the argument ``template_name`` (see below).

    **Arguments**

    ``backend``
        The dotted Python import path to the backend class to
        use. Required.

    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context. Optional.

    ``success_url``
        The name of a URL pattern to redirect to on successful
        acivation. This is optional; if not specified, this will be
        obtained by calling the backend's
        ``post_activation_redirect()`` method.

    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``registration/activate.html``.

    ``\*\*kwargs``
        Any keyword arguments captured from the URL, such as an
        activation key, which will be passed to the backend's
        ``activate()`` method.

    **Context:**

    The context will be populated from the keyword arguments captured
    in the URL, and any extra variables supplied in the
    ``extra_context`` argument (see above).

    **Template:**

    registration/activate.html or ``template_name`` keyword argument.

    """
    backend = get_backend(backend)
    account = backend.activate(request, **kwargs)

    if account:
        if not account.has_usable_password() and account.email:
            account.password = User.objects.make_random_password()
            account.save()

            uid = urlsafe_base64_encode(force_bytes(account.pk))
            token = token_generator.make_token(account)
            protocol = 'https' if request.is_secure() else 'http'

            if is_admin_site:
                domain = request.get_host()
            else:
                current_site = get_current_site(request)
                domain = current_site.domain

            return HttpResponseRedirect("{protocol}://{domain}{url}".format(
                protocol=protocol,
                domain=domain,
                url=reverse('password_reset_confirm', kwargs=dict(uidb64=uid, token=token)),
            ))

        if success_url is None:
            to, args, kwargs = backend.post_activation_redirect(
                request, account)
            return redirect(to, *args, **kwargs)
        else:
            return redirect(success_url)

    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    return render_to_response(template_name,
                              kwargs,
                              context_instance=context)


@sensitive_post_parameters()
@csrf_protect
@never_cache
def register(request, backend, success_url=None, form_class=None,
             disallowed_url='registration_disallowed',
             template_name='registration/registration_form.html',
             extra_context=None):
    """
    Allow a new user to register an account.

    The actual registration of the account will be delegated to the
    backend specified by the ``backend`` keyword argument (see below);
    it will be used as follows:

    1. The backend's ``registration_allowed()`` method will be called,
       passing the ``HttpRequest``, to determine whether registration
       of an account is to be allowed; if not, a redirect is issued to
       the view corresponding to the named URL pattern
       ``registration_disallowed``. To override this, see the list of
       optional arguments for this view (below).

    2. The form to use for account registration will be obtained by
       calling the backend's ``get_form_class()`` method, passing the
       ``HttpRequest``. To override this, see the list of optional
       arguments for this view (below).

    3. If valid, the form's ``cleaned_data`` will be passed (as
       keyword arguments, and along with the ``HttpRequest``) to the
       backend's ``register()`` method, which should return the new
       ``User`` object.

    4. Upon successful registration, the backend's
       ``post_registration_redirect()`` method will be called, passing
       the ``HttpRequest`` and the new ``User``, to determine the URL
       to redirect the user to. To override this, see the list of
       optional arguments for this view (below).

    **Required arguments**

    None.

    **Optional arguments**

    ``backend``
        The dotted Python import path to the backend class to use.

    ``disallowed_url``
        URL to redirect to if registration is not permitted for the
        current ``HttpRequest``. Must be a value which can legally be
        passed to ``django.shortcuts.redirect``. If not supplied, this
        will be whatever URL corresponds to the named URL pattern
        ``registration_disallowed``.

    ``form_class``
        The form class to use for registration. If not supplied, this
        will be retrieved from the registration backend.

    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context.

    ``success_url``
        URL to redirect to after successful registration. Must be a
        value which can legally be passed to
        ``django.shortcuts.redirect``. If not supplied, this will be
        retrieved from the registration backend.

    ``template_name``
        A custom template to use. If not supplied, this will default
        to ``registration/registration_form.html``.

    **Context:**

    ``form``
        The registration form.

    Any extra variables supplied in the ``extra_context`` argument
    (see above).

    **Template:**

    registration/registration_form.html or ``template_name`` keyword
    argument.

    """
    backend = get_backend(backend)
    if not backend.registration_allowed(request):
        return redirect(disallowed_url)
    if form_class is None:
        form_class = backend.get_form_class(request)

    if request.method == 'POST':
        form = form_class(data=request.POST, files=request.FILES)
        if form.is_valid():
            new_user = backend.register(request, **form.cleaned_data)
            if success_url is None:
                to, args, kwargs = backend.post_registration_redirect(
                    request, new_user)
                return redirect(to, *args, **kwargs)
            else:
                return redirect(success_url)
    else:
        form = form_class()

    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    return render_to_response(template_name,
                              {'form': form},
                              context_instance=context)


if settings.LOGIN_ON_ACTIVATION:
    def login_on_activation(user, request, **kwargs):
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
    signals.user_activated.connect(login_on_activation)
