# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import template

from dfw.core.templatetags.simple_tags import resolveattr as _resolveattr

EMPTY_VALUES = ('', None)

register = template.Library()


@register.simple_tag(takes_context=True)
def get_icon(context, obj):
    return context['get_icon_fn'](obj)


@register.simple_tag(takes_context=True)
def resolve(context, item, attr, view=None, *args, **kwargs):
    _attr = None
    if _attr in EMPTY_VALUES:
        _view = context.get('view') or view
        _attr = getattr(_view, attr, None)
        if _attr:
            _attr = _attr(context, item, attr, *args, **kwargs)
    if _attr in EMPTY_VALUES:
        if item:
            _attr = _resolveattr(item, attr)
    return _attr
