"""Compatibility functions between Jinja2 and Django.

General notes:

  - The Django ``stringfilter`` decorator is supported, but should not be
    used when writing filters specifically for Jinja: It will lose the
    attributes attached to the filter function by Jinja's
    ``environmentfilter`` and ``contextfilter`` decorators, when used
    in the wrong order.

    Maybe coffin should provide a custom version of stringfilter.

  - While transparently converting filters between Django and Jinja works
    for the most part, there is an issue with Django's
    ``mark_for_escaping``, as Jinja does not support a similar mechanism.
    Instead, for Jinja, we escape such strings immediately (whereas Django
    defers it to the template engine).
"""
from __future__ import absolute_import

import inspect
from functools import wraps

from django.utils.safestring import SafeData, EscapeData, mark_safe, mark_for_escaping
from django.utils.timezone import template_localtime

from jinja2 import Markup, environmentfilter, contextfilter, Undefined


__all__ = (
    'DJANGO', 'JINJA2',
    'django_filter_to_jinja2',
    'jinja2_filter_to_django',
    'guess_filter_type',)


DJANGO = 'django'
JINJA2 = 'jinja2'


def django_filter_to_jinja2(filter_func):
    """
    Note: Due to the way this function is used by
    ``coffin.template.Library``, it needs to be able to handle native
    Jinja2 filters and pass them through unmodified. This necessity
    stems from the fact that it is not always possible to determine
    the type of a filter.
    """
    if guess_filter_type(filter_func)[0] == JINJA2:
        return filter_func

    def _convert_out(v, o=None):
        if getattr(filter_func, 'is_safe', False) and isinstance(o, SafeData):
            v = mark_safe(v)
        elif isinstance(o, EscapeData):
            v = mark_for_escaping(v)
        if isinstance(v, SafeData):
            return Markup(v)
        if isinstance(v, EscapeData):
            return Markup.escape(v)       # not 100% equivalent, see mod docs
        return v

    def _convert_in(v):
        if isinstance(v, Undefined):
            # Essentially the TEMPLATE_STRING_IF_INVALID default
            # setting. If a non-default is set, Django wouldn't apply
            # filters. This is something that we neither can nor want to
            # simulate in Jinja.
            return ''
        if isinstance(v, Markup):
            v = mark_safe(v)
        return v

    def conversion_wrapper(value, *args, **kwargs):
        value = _convert_in(value)
        result = filter_func(value, *args, **kwargs)
        return _convert_out(result, value)

    # Jinja2 supports a similar machanism to Django's
    # ``needs_autoescape`` filters: environment filters. We can
    # thus support Django filters that use it in Jinja2 with just
    # a little bit of argument rewriting.
    if getattr(filter_func, 'needs_autoescape', False):
        def get_autoescape_wrapper(conversion_wrapper):
            def autoescape_wrapper(environment, value, *args, **kwargs):
                kwargs['autoescape'] = environment.autoescape
                return conversion_wrapper(value, *args, **kwargs)
            return environmentfilter(autoescape_wrapper)
        conversion_wrapper = get_autoescape_wrapper(conversion_wrapper)

    if getattr(filter_func, 'expects_localtime', False):
        def get_localtime_wrapper(conversion_wrapper):
            def localtime_wrapper(context, value, *args, **kwargs):
                value = template_localtime(value, use_tz=context.use_tz)
                return conversion_wrapper(value, *args, **kwargs)
            return contextfilter(localtime_wrapper)
        conversion_wrapper = get_localtime_wrapper(conversion_wrapper)

    _dec = conversion_wrapper

    # Include a reference to the real function (used to check original
    # arguments by the template parser, and to bear the 'is_safe' attribute
    # when multiple decorators are applied).
    _dec._decorated_function = getattr(filter_func, '_decorated_function', filter_func)

    return wraps(filter_func)(_dec)


def jinja2_filter_to_django(filter_func):
    """
    Note: Due to the way this function is used by
    ``coffin.template.Library``, it needs to be able to handle native
    Django filters and pass them through unmodified. This necessity
    stems from the fact that it is not always possible to determine
    the type of a filter.
    """
    if guess_filter_type(filter_func)[0] == DJANGO:
        return filter_func

    def _convert_out(v, o=None):
        # TODO: for now, this is not even necessary: Markup strings have
        # a custom replace() method that is immume to Django's escape()
        # attempts.
        #if isinstance(v, Markup):
        #    return SafeUnicode(v)         # jinja is always unicode
        # ... Jinja does not have a EscapeData equivalent
        return v

    def _dec(value, *args, **kwargs):
        result = filter_func(value, *args, **kwargs)
        return _convert_out(result, value)

    # Include a reference to the real function (used to check original
    # arguments by the template parser, and to bear the 'is_safe' attribute
    # when multiple decorators are applied).
    _dec._decorated_function = getattr(filter_func, '_decorated_function', filter_func)

    return wraps(filter_func)(_dec)


def guess_filter_type(filter_func):
    """Returns a 2-tuple of (type, can_be_ported).

    ``type`` is one of DJANGO, JINJA2, or ``False`` if the type can
    not be determined.

    ``can_be_ported`` is ``True`` if we believe the filter could be
    ported to the other engine, respectively, or ``False`` if we know
    it can't.

    TODO: May not yet use all possible clues, e.g. decorators like
    ``stringfilter``.
    TOOD: Needs tests.
    """
    if hasattr(filter_func, 'contextfilter') or \
       hasattr(filter_func, 'environmentfilter'):
            return JINJA2, False

    args = inspect.getargspec(filter_func)
    if len(args[0]) - (len(args[3]) if args[3] else 0) > 2:
        return JINJA2, False

    if hasattr(filter_func, 'needs_autoescape'):
        return DJANGO, True

    # Looks like your run of the mill Python function, which are
    # easily convertible in either direction.
    return False, True
