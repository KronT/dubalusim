# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals  # >> important to ease the migration to python3

from django.views.generic import CreateView, ListView
from django.core import urlresolvers

from .models import MySampleModel
from .forms import MySampleForm


class ItemListView(ListView):
    model = MySampleModel
    template_name = 'mysampleapp/item_list.html'

    def get_queryset(self):
        return self.model.objects.order_by('name')

item_list = ItemListView.as_view()


class ItemCreateView(CreateView):
    model = MySampleModel
    form_class = MySampleForm
    template_name = 'mysampleapp/item_create.html'
    success_url = urlresolvers.reverse_lazy('item-list')

item_create = ItemCreateView.as_view()
