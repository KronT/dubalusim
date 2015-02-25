# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals, print_function

import string
import random
import hashlib
import phonenumbers

from django.conf import settings
from django import template
from django.utils.encoding import force_text
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils import six

from typecast import Money, try_number

from dfw.utils.cache import cache_seq
from dfw.utils.json import json

CODE_CHARS = string.ascii_lowercase + string.digits

register = template.Library()


cache_seq = register.assignment_tag()(cache_seq)


@register.block_tag
def jsmin(body, *args):
    return body()


@register.simple_tag
def repeat(value, times):
    if not isinstance(times, (int, long)):
        times = len(force_text(times))
    return force_text(value) * times


@register.filter(name='getattr')
def resolveattr(obj, name):
    value = None
    names = name.split('__')
    for name in names:
        value = getattr(obj, name, None)
        if callable(value):
            value = value()
        obj = value
    return value


@register.assignment_tag()
def uniqueid(length=16):
    return ''.join(random.sample(CODE_CHARS, length))


@register.filter(name='hash')
def do_hash(value):
    value = hash(value)
    return value


@register.filter(name='md5')
@stringfilter
def do_md5(value, encoding='utf-8'):
    value = hashlib.md5(value.encode(encoding)).hexdigest()
    return value


@register.filter(name='range')
def do_range(*args):
    return range(*[int(a or 0) for a in args])


if settings.DEBUG:
    @register.filter(name='repr')
    def do_repr(value):
        value = repr(value)
        return value

    @register.filter(name='print')
    def do_print(value):
        print(value)
        return ''


@register.filter(name='text')
@stringfilter
def do_text(value):
    return value


@register.filter(is_safe=False, name='json')
def do_json(value):
    try:
        return mark_safe(json.dumps(value))
    except:
        return ''


@register.filter(is_safe=False, name='mul')
def do_mul(a, b):
    a = try_number(a)
    b = try_number(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, float) or isinstance(b, float):
            return a * b
        else:
            return int(a * b)
    try:
        return a * b
    except Exception:
        return ''


@register.filter(name='phonenumber')
def phonenumber(phone_number, country=None, fmt='INTERNATIONAL'):
    try:
        fmt = getattr(phonenumbers.PhoneNumberFormat, fmt)
        numobj = phonenumbers.parse(phone_number, country)
        return phonenumbers.format_number(numobj, fmt)
    except phonenumbers.NumberParseException:
        return phone_number


@register.filter(name='money')
def money(value, symbol="$", decimals=2):
    try:
        return Money(value, symbol, decimals)
    except:
        return value


@register.filter(name='in')
def do_in(a, b):
    if isinstance(b, six.string_types) and ',' in b:
        b = b.split(',')
    return a in b
