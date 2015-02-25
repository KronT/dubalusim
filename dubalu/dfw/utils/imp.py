# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import

import os
import sys
import imp


def find_module(name, path=None):
    """
    Tries finding a module without importing stuff

    Returns path of the module if found

    """
    path = sys.path if path is None else path
    for name in name.split('.'):
        file, pathname, desc = imp.find_module(name, path)
        path = [pathname]
    return file, pathname, desc


def direct_import(name, path=None):
    """
    Direct import a module (without importing the package's __init__)

    """
    path = sys.path if path is None else path
    file, pathname, desc = find_module(name, path)
    module_name = name.split('.')[-1]
    try:
        mod = sys.modules[module_name]
    except KeyError:
        sys.path = [os.path.dirname(pathname)] + path
        mod = __import__(module_name)
        del sys.modules[module_name]
        sys.path = path
    return mod
