# -*- coding: utf-8 -*-

import json as json_

from django import template
from django.utils.html import escape, conditional_escape
from django.utils.encoding import force_text

from ..layout import basic_param_encoder

register = template.Library()


def _get_attrs(**kwargs):
    attrs = {}
    for k, v in kwargs.items():
        k = k.replace('_', '-')
        v = escape(v)
        attrs[k] = v

    return attrs


def _flatatt(attrs):
    """
    Taken from crispy_forms, which was also taken from django.core.utils
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs.  It is assumed that the keys do not need to be XML-escaped.
    If the passed dictionary is empty, then return an empty string.
    """
    return u''.join([u' %s="%s"' % (k.replace('_', '-'), conditional_escape(v)) for k, v in attrs.items()])


def _walk_render(item):
        if isinstance(item, (tuple, list)):
            return [_walk_render(i, ) for i in item]
        elif isinstance(item, dict):
            return dict((
                _walk_render(k),
                _walk_render(v)
            ) for k, v in item.items())
        elif isinstance(item, (int, long, float, bool)):
            return item
        else:
            return force_text(item)


@register.inclusion_tag('crispy_extra_fields/lazyform_loader.html', takes_context=True)
def lazyloader(context, form, value='', field_name=None, data_provide='lazy-loader',
        method='post', tag='button', element_attr="action", icon_class='', icon_first=True,
        url=None, url_encoder=None, included_params=(), url_encoder_kwargs={}, css_class='',
        **kwargs):
    attrs = kwargs
    attrs['data_provide'] = data_provide

    attrs = _get_attrs(**attrs)

    if url:
        attrs[element_attr] = url
    else:
        url_encoder = url_encoder or basic_param_encoder
        attrs[element_attr] = url_encoder(form, None, context, *included_params, **url_encoder_kwargs)

    template_context = dict(
        value=value,
        field_classes=css_class,
        icon_class=icon_class,
        icon_first=icon_first,
        flat_attrs=_flatatt(attrs),
        tag=tag,
    )
    return template_context


@register.simple_tag
def json(dictionary):
    dictionary = _walk_render(dictionary)
    _json = json_.dumps(dictionary)
    return escape(_json)


@register.inclusion_tag('crispy_extra_fields/inline_edit.html', takes_context=True)
def inline_edit(context, form, field_name, detail_helper='detail_helper',
        loadable_detail_helper='loadable_detail_helper',
        edit_helper='edit_helper', url_name='lazyform-inline-edit', css_class=""):

    kwargs = {}
    kwargs.update(dict(
        helper=edit_helper,
        url_name=url_name,
    ))
    if len(form.fields) == 1:
        if css_class:
            css_class += " "
        css_class += "single-inline"

    template_context = dict(
        context,
        form=form,
        pk=form.instance.pk,
        field_name=field_name,
        url=basic_param_encoder(form, None, context, **kwargs),
        detail_helper=detail_helper,
        loadable_detail_helper=loadable_detail_helper,
        css_class=css_class,
        can_edit_item=form.can_edit_item(context['request']),
    )
    return template_context
