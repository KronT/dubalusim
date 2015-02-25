# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals, print_function

import sys


def extend_settings(glob, include=None, exclude=None, extra=None):
    """
    Extends the settings in glob with the settings modules loaded from INSTALLED_APPS

    Example:
        extend_settings(globals())
    """
    from dfw.utils.imp import direct_import

    if extra is None:
        extra = []
    else:
        extra = list(extra)

    INSTALLED_APPS = glob['INSTALLED_APPS'] = list(glob['INSTALLED_APPS'])

    SETTINGS_APPS = [app_label for app_label in INSTALLED_APPS if app_label not in extra]
    SETTINGS_APPS += extra

    if exclude is None:
        exclude = []
    else:
        exclude = list(exclude)
    exclude.extend([glob['__name__'], __name__])

    def extend_app(app_label, include, exclude, extra_exclude=None):
        if extra_exclude and app_label in extra_exclude:
            return

        settings_mod_name = '%s.settings' % app_label
        if exclude:
            for x in exclude:
                if hasattr(x, 'match'):
                    if x.match(settings_mod_name):
                        return
                else:
                    if x == settings_mod_name or x == app_label:
                        return
        if include:
            for x in include:
                if hasattr(x, 'match'):
                    if not x.match(settings_mod_name):
                        return
                else:
                    if x != settings_mod_name and x != app_label:
                        return

        try:
            mod = direct_import(settings_mod_name)
        except ImportError:
            return

        exclude.append(settings_mod_name)

        for name in dir(mod):
            if not name.startswith('_'):
                attr = getattr(mod, name)
                if '<django.conf.LazySettings object at' in repr(attr):
                    print("App %s imported django settings in it's setting module! Problems might arise later on." % app_label, file=sys.stderr)
                if name == 'INSTALLED_APPS':
                    oi = INSTALLED_APPS.index(app_label) + 1
                    ot = SETTINGS_APPS.index(app_label) + 1
                    for i, app in enumerate(app for app in attr if app not in INSTALLED_APPS):
                        SETTINGS_APPS.insert(ot + i, app)
                        if app_label in extra:
                            INSTALLED_APPS.append(app)
                        else:
                            INSTALLED_APPS.insert(oi + i, app)
                elif name == 'PLUGINS':
                    plugins = glob.get('PLUGINS')
                    if plugins is None:
                        plugins = glob['PLUGINS'] = {}
                    for _hook, _plugins in attr.items():
                        if _hook not in plugins:
                            plugins[_hook] = []
                        plugins[_hook].extend(v for v in _plugins if v not in plugins[_hook])
                elif name == 'DEPENDENCIES':
                    dependencies = glob.get('DEPENDENCIES')
                    if dependencies is None:
                        dependencies = glob['DEPENDENCIES'] = {}
                    dependencies[app_label] = attr
                elif name not in glob:
                    glob[name] = attr
                elif isinstance(glob[name], dict) and isinstance(attr, dict):
                    glob[name] = dict(glob[name], **attr)
                elif isinstance(glob[name], (tuple, list)) and isinstance(attr, (tuple, list)):
                    cast = tuple if isinstance(glob[name], tuple) else list
                    glob[name] = cast(glob[name]) + cast(attr)
                else:
                    glob[name] = attr
        # print("Settings extended from %s" % settings_mod_name)

    for app_label in SETTINGS_APPS:
        extend_app(app_label, include, exclude)
