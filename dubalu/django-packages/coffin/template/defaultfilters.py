"""Coffin automatically makes Django's builtin filters available in Jinja2,
through an interop-layer.

However, Jinja 2 provides room to improve the syntax of some of the
filters. Those can be overridden here.

TODO: Most of the filters in here need to be updated for autoescaping.
"""
from __future__ import absolute_import

from datetime import datetime, tzinfo

try:
    import pytz
except ImportError:
    pytz = None

from django.utils import six
from django.utils import timezone

from jinja2.runtime import Undefined
from jinja2 import filters

from . import Library

register = Library()


def url(view_name, *args, **kwargs):
    """This is an alternative to the {% url %} tag. It comes from a time
    before Coffin had a port of the tag.
    """
    from .defaulttags import URLExtension
    return URLExtension._reverse(view_name, args, kwargs)
register.jinja2_filter(url, jinja2_only=True)
register.object(url)


@register.jinja2_filter(jinja2_only=True)
def timesince(value, *arg):
    if value is None or isinstance(value, Undefined):
        return u''
    from django.utils.timesince import timesince
    return timesince(value, *arg)


@register.jinja2_filter(jinja2_only=True)
def timeuntil(value, *args):
    if value is None or isinstance(value, Undefined):
        return u''
    from django.utils.timesince import timeuntil
    return timeuntil(value, *args)


@register.jinja2_filter(jinja2_only=True)
def truncatewords(value, length):
    # Jinja2 has it's own ``truncate`` filter that supports word
    # boundaries and more stuff, but cannot deal with HTML.
    try:
        from django.utils.text import Truncator
    except ImportError:
        from django.utils.text import truncate_words  # Django < 1.6
    else:
        truncate_words = lambda value, length: Truncator(value).words(length)
    return truncate_words(value, int(length))


@register.jinja2_filter(jinja2_only=True)
def truncatewords_html(value, length):
    try:
        from django.utils.text import Truncator
    except ImportError:
        from django.utils.text import truncate_html_words  # Django < 1.6
    else:
        truncate_html_words = lambda value, length: Truncator(value).words(length, html=True)
    return truncate_html_words(value, int(length))


@register.jinja2_filter(jinja2_only=True)
def pluralize(value, s1='s', s2=None):
    """Like Django's pluralize-filter, but instead of using an optional
    comma to separate singular and plural suffixes, it uses two distinct
    parameters.

    It also is less forgiving if applied to values that do not allow
    making a decision between singular and plural.
    """
    if s2 is not None:
        singular_suffix, plural_suffix = s1, s2
    else:
        plural_suffix = s1
        singular_suffix = ''

    try:
        if int(value) != 1:
            return plural_suffix
    except TypeError:  # not a string or a number; maybe it's a list?
        if len(value) != 1:
            return plural_suffix
    return singular_suffix


@register.jinja2_filter(jinja2_only=True)
def floatformat(value, arg=-1):
    """Builds on top of Django's own version, but adds strict error
    checking, staying with the philosophy.
    """
    from django.template.defaultfilters import floatformat
    from ..interop import django_filter_to_jinja2
    arg = int(arg)  # raise exception
    result = django_filter_to_jinja2(floatformat)(value, arg)
    if result == '':  # django couldn't handle the value
        raise ValueError(value)
    return result


@register.jinja2_filter(jinja2_only=True)
def default(value, default_value=u'', boolean=True):
    """Make the default filter, if used without arguments, behave like
    Django's own version.
    """
    return filters.do_default(value, default_value, boolean)


# HACK: datetime is an old-style class, create a new-style equivalent
# so we can define additional attributes.
class datetimeobject(datetime, object):
    pass


# Template filters

@register.filter
def localtime(value):
    """
    Converts a datetime to local time in the active time zone.

    This only makes sense within a {% localtime off %} block.
    """
    return do_timezone(value, timezone.get_current_timezone())


@register.filter
def utc(value):
    """
    Converts a datetime to UTC.
    """
    return do_timezone(value, timezone.utc)


@register.filter('timezone')
def do_timezone(value, arg):
    """
    Converts a datetime to local time in a given time zone.

    The argument must be an instance of a tzinfo subclass or a time zone name.
    If it is a time zone name, pytz is required.

    Naive datetimes are assumed to be in local time in the default time zone.
    """
    if not isinstance(value, datetime):
        return ''

    # Obtain a timezone-aware datetime
    try:
        if timezone.is_naive(value):
            default_timezone = timezone.get_default_timezone()
            value = timezone.make_aware(value, default_timezone)
    # Filters must never raise exceptions, and pytz' exceptions inherit
    # Exception directly, not a specific subclass. So catch everything.
    except Exception:
        return ''

    # Obtain a tzinfo instance
    if isinstance(arg, tzinfo):
        tz = arg
    elif isinstance(arg, six.string_types) and pytz is not None:
        try:
            tz = pytz.timezone(arg)
        except pytz.UnknownTimeZoneError:
            return ''
    else:
        return ''

    result = timezone.localtime(value, tz)

    # HACK: the convert_to_local_time flag will prevent
    #       automatic conversion of the value to local time.
    result = datetimeobject(result.year, result.month, result.day,
                            result.hour, result.minute, result.second,
                            result.microsecond, result.tzinfo)
    result.convert_to_local_time = False
    return result
