# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals, print_function

import os
import datetime

# For django to work, we need to populate apps and models as soon as possible
# If the apps have not yet been populated by now (as is the case when using uwsgi),
# populate.
from django.db.models.loading import cache
cache._populate()

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
# from django.utils.functional import memoize

from django.views.decorators.http import last_modified
from django.views.decorators.cache import cache_page
from django.views.i18n import javascript_catalog

# from dfw.sections.urls_base import get_urlresolver as get_sections_urlresolver


# Admin:
# from django.contrib import admin
# admin.autodiscover()


# handler400 = settings.HANDLER400
# handler403 = settings.HANDLER403
# handler404 = settings.HANDLER404
# handler500 = settings.HANDLER500


JSI18N_DATE_FILE = getattr(settings, 'JSI18N_DATE_FILE', '/tmp/jsi18n')
try:
    JSI18N_DATE = os.path.getmtime(JSI18N_DATE_FILE)
except OSError:
    JSI18N_DATE = float(datetime.datetime.now().strftime('%s'))
    open(JSI18N_DATE_FILE, 'a').close()
jsi18n_date = datetime.datetime.fromtimestamp(JSI18N_DATE)


# The value of JSI18N_DATE must change when translations change.
@last_modified(lambda req, **kw: jsi18n_date)
@cache_page(86400, key_prefix='js18n-%s' % JSI18N_DATE)
def cached_javascript_catalog(request, domain='djangojs', packages=None):
    if packages is None:
        packages = tuple(settings.INSTALLED_APPS) + ('django.conf',)
    return javascript_catalog(request, domain, packages)


# Default base urlpatterns:
urlpatterns = patterns('')

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, view='django.contrib.staticfiles.views.serve')

urlpatterns += patterns('',
    # url(r'^autocomplete/', include('dfw.autocomplete.urls')),
    # url(r'^impersonate/', include('dfw.impersonation.urls')),

    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^i18n/js/$', cached_javascript_catalog, name='javascript_catalog'),

    # url(r'^morsels/(?P<__params__>[^/]+)/', include('dfw.morsels.urls_base', app_name='morsel')),
)

# urlconf_module = include('dfw.notification.urls')[0]
# urlpatterns += getattr(urlconf_module, 'urlpatterns', urlconf_module)

# urlconf_module = include('dfw.pluggables.urls_base')[0]
# urlpatterns += getattr(urlconf_module, 'urlpatterns', urlconf_module)

if settings.PROJECT_NAME:
    urlconf_module = include('%s.urls' % settings.PROJECT_NAME)[0]
    urlpatterns += getattr(urlconf_module, 'urlpatterns', urlconf_module)

urlconf_module = include('dfw.contrib.pages.urls')[0]
urlpatterns += getattr(urlconf_module, 'urlpatterns', urlconf_module)


# def get_urls(project_name, project_suffix):
#     project_urls = patterns('', get_sections_urlresolver(project_name, project_suffix)) + urlpatterns
#     return type(b'ProjectUrls', (object,), dict(
#         handler400=handler400,
#         handler403=handler403,
#         handler404=handler404,
#         handler500=handler500,
#         urlpatterns=project_urls,
#     ))()
# get_urls._cache = {}
# get_urls = memoize(get_urls, get_urls._cache, 2)
