# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import

from django import template

from templatetag_sugar.parser import Optional, Variable, Assignment


register = template.Library()


@register.advanced_tag(takes_context=True,
    syntax=[Optional([Variable('value', is_content=True)]), 'as', Assignment()],
    blocks=Optional())
def capture(context, body, value=None):
    """
        {% capture myvar as var_name %}

        {% capture "string" as var_name %}

        {% capture as var_name %}
          ....
        {% endcapture %}
    """
    if body:
        value = body()
    return value
