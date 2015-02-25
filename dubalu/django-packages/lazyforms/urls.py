# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, print_function

from django.conf.urls import patterns, url

urlpatterns = patterns('lazyforms.views',
    url(r'^load/(?P<params>.+)/$', 'load', name='lazyform-load'),
    url(r'^validate/(?P<params>.+)/$', 'validate', name='lazyform-validate'),

    url(r'^inline/(?P<params>.+)/$', 'inline_edit', name='lazyform-inline-edit'),
)
