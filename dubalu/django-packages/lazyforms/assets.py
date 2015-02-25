# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

from django_assets import Bundle

from dfw.contrib.bundles import Bundles


class LazyLoader(Bundles):
    """
    Functionality to load lazyforms.

    """
    js = Bundle(
        'src/js/jquery.lazyloader.js',
    )


class InlineEdit(Bundles):
    js = Bundle(
        'src/js/inline_edit.js',
    )

    css = Bundle(
        'src/css/inline_edit.scss',
    )
