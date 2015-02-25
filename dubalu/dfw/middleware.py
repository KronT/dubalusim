# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

import re

from django.conf import settings
from django.http import HttpResponseServerError
from django.utils.encoding import force_text
from django.utils.importlib import import_module
from django.utils.functional import memoize

from recursiveformat import recursive_format

import logging
logger = logging.getLogger(__name__)


_HTML_TYPES = ('text/html', 'application/xhtml+xml')


def replace_insensitive(string, target, replacement):
    """
    Similar to string.replace() but is case insensitive.
    Code borrowed from:
    http://forums.devshed.com/python-programming-11/case-insensitive-string-replace-490921.html
    """
    no_case = string.lower()
    index = no_case.rfind(target.lower())
    if index >= 0:
        return string[:index] + replacement + string[index + len(target):]
    else:  # no results so return the original string
        return string


def get_project_settings():
    projects = {}
    for project in settings.SETTINGS:
        project_settings = {}
        regex, modules = settings.SETTINGS[project]
        if not isinstance(modules, (tuple, list)):
            modules = [modules]
        for module in modules:
            if isinstance(module, dict):
                _project_settings = module
            else:
                module = import_module(module)
                _project_settings = dict((k, v) for k, v in module.__dict__.items() if k.isupper() and k[0] != '_')
            _all_settings = settings.default_settings.__dict__.copy()
            _all_settings.update(_project_settings)
            recursive_format(_project_settings, **_all_settings)
            project_settings.update(_project_settings)
        project_name, _, project_suffix = project.partition('.')
        projects[project] = (re.compile(regex), (project_name, project_suffix, project_settings))
    return projects
get_project_settings._cache = {}
get_project_settings = memoize(get_project_settings, get_project_settings._cache, 0)


class DynamicSettingsMiddleware(object):
    """
    This middleware is in chare of resetting and setting up dynamic settings,
    including PROJECT_NAME, PROJECT_SUFFIX and other settings in a per-request
    basis.
    """
    if not settings.TEST:
        def process_request(self, request):
            projects = get_project_settings()
            host = request.get_host()
            try:
                regex, (project_name, project_suffix, project_settings) = projects[request.META['HTTP_X_PROJECT']]
            except KeyError:
                logger.warning("X-Project not set in the request headers, falling back to regexp resolution!")
                for regex, (project_name, project_suffix, project_settings) in projects.values():
                    if regex.search(host):
                        break
                else:
                    if projects:
                        return HttpResponseServerError("No project found for the given host: %s" % host)
                    project_suffix = project_name = None
            if project_suffix:
                project = '%s.%s' % (project_name, project_suffix)
            else:
                project = project_name

            # Settings and urls override:
            from raven.contrib.django.models import client
            from .urls import get_urls
            settings.clear(project_settings)
            settings.PROJECT_NAME, settings.PROJECT_SUFFIX = project_name, project_suffix
            settings.PROJECT = project
            client.set_dsn(settings.RAVEN_CONFIG['dsn'])
            urlpatterns = get_urls(settings.PROJECT_NAME, settings.PROJECT_SUFFIX)
            request.urlconf = urlpatterns

        def process_response(self, request, response):
            from raven.contrib.django.models import client
            settings.clear()  # If not running tests, cleanup settings (requires patch #12737-thread_local_settings.diff):
            client.set_dsn(settings.RAVEN_CONFIG['dsn'])
            return response

        # def process_exception(self, request, exception):
        #     import ipdb; ipdb.set_trace()


class ProfilerMiddleware(object):
    tag = '</body>'

    def process_request(self, request):
        request.profiler = []

    def process_response(self, request, response):
        if getattr(request, 'profiler', None):
            if ('gzip' not in response.get('Content-Encoding', '') and
                    response.get('Content-Type', '').split(';')[0] in _HTML_TYPES):
                content = ''
                for profiler in request.profiler:
                    content += '\n<div class="profiler">%s</div>\n' % profiler
                response.content = replace_insensitive(
                    force_text(response.content, encoding=settings.DEFAULT_CHARSET),
                    self.tag,
                    force_text(content + self.tag))
                if response.get('Content-Length', None):
                    response['Content-Length'] = len(response.content)
        return response
