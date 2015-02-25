# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals  # >> important to ease the migration to python3

from django.views.generic import CreateView

from .models import MySampleModel
from .forms import MySampleForm


class ItemCreateView(CreateView):
    model = MySampleModel
    form_class = MySampleForm
    template_name = 'mysampleapp/create_item.html'

item_create = ItemCreateView.as_view()
