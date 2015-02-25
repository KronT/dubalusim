# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

import hashlib

from django.utils.encoding import force_bytes
from django.utils.http import urlquote
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key


def make_fragment_key(fragment_name, vary_on=None, fragment_key_template='dfw.cache.%s.%s'):
    if vary_on is None:
        vary_on = ()
    key = ':'.join([urlquote(var) for var in vary_on])
    args = hashlib.md5(force_bytes(key))
    return fragment_key_template % (fragment_name, args.hexdigest())


def cache_seq_incr(fragm_name, *vary_on):
    cache_key = make_template_fragment_key(fragm_name, vary_on)
    try:
        seq = cache.incr(cache_key)
    except ValueError:
        seq = 1
        cache.set(cache_key, seq)
    return seq


def cache_seq(fragm_name, *vary_on):
    cache_key = make_template_fragment_key(fragm_name, vary_on)
    seq = cache.get(cache_key) or 0
    return '{0}:{1}'.format(cache_key, seq)


def cache_seq_multi(frags):
    cache_keys = [make_template_fragment_key(fragm_name, vary_on) for fragm_name, vary_on in frags]
    all_seq = cache.get_many(cache_keys)
    return ['{0}:{1}'.format(cache_key, all_seq.get(cache_key) or 0) for cache_key in cache_keys]
