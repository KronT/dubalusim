# -*- coding: utf-8 -*-
"""
Dubalu Framework: CFDI Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from django_assets import Bundle, register

from dfw.contrib.bundles.jquery import jQuery, jQueryExtra
from dfw.contrib.bundles.bootstrap import Bootstrap, BootstrapExtra
from dfw.contrib.bundles.bootstrapvalidator import BootstrapValidator
from dfw.contrib.bundles.datepicker import Datepicker
from dfw.contrib.bundles.selectpicker import Selectpicker
from dfw.contrib.bundles.tokenfield import Tokenfield
from dfw.contrib.bundles.formset import Formset
from dfw.contrib.bundles.ezpz import Ezpz
from dfw.contrib.bundles.ladda import Ladda
from dfw.contrib.bundles.ckeditor import CKEditor
from dfw.contrib.bundles.typeahead import Typeahead

from endless_pagination.assets import EndlessPagination
from lazyforms.assets import LazyLoader, InlineEdit


class Dubalu(Bundle):
    js = Bundle(
        'src/js/dubalu.js',
        # 'src/js/theme.js',
        # 'src/js/session_menu.js',
    )

    css = Bundle(
        'src/sass/frameworks/font-dubalu.scss',
        'src/css/dubalu.scss',
        # 'src/css/theme.scss',

        # 'src/css/rtd.scss',  # for documentation
    )


register('js_basic', Bundle(
    jQuery.js,
    Bootstrap.js,
    filters=('iife', 'uglifyjs',),
    output='basic.js',
))


register('js_all', Bundle(
    jQueryExtra.js,
    BootstrapExtra.js,
    Typeahead.js,
    Datepicker.js,
    Selectpicker.js,
    Tokenfield.js,
    Formset.js,
    LazyLoader.js,
    InlineEdit.js,
    Ezpz.js,
    BootstrapValidator.js,
    Ladda.js,
    EndlessPagination.js,

    filters=('iife', 'uglifyjs',),
    output='common.js',
))


register('js_theme', Bundle(
    Dubalu.js,
    filters=('iife', 'uglifyjs',),
    output='theme.js',
))


################################################################################

register('css_basic', Bundle(
    jQuery.css,
    Bootstrap.css,
    filters=('pyscss', 'autoprefixer',),
    output='basic.css',
))

register('css_all', Bundle(
    jQueryExtra.css,
    BootstrapExtra.css,
    Typeahead.css,
    Datepicker.css,
    Selectpicker.css,
    Tokenfield.css,
    Formset.css,
    InlineEdit.css,
    Ezpz.css,
    BootstrapValidator.css,
    Ladda.css,
    EndlessPagination.css,

    filters=('pyscss', 'autoprefixer',),
    output='common.css',
))


register('css_theme', Bundle(
    Dubalu.css,
    filters=('pyscss', 'autoprefixer',),
    output='theme.css',
))

# Internet Explorer specific assets:

register('js_ie7', Bundle(
    'src/js/ie/ie7.js',
    'src/js/ie/placeholders.js',
    filters=('iife', 'uglifyjs',),
    output='ie7.js',
))

register('css_ie7', Bundle(
    'src/css/bootstrap-ie7.css',
    output='ie7.css',
))

register('js_ie8', Bundle(
    'src/js/ie/ie8.js',
    'src/js/ie/placeholders.js',
    filters=('iife', 'uglifyjs',),
    output='ie8.js',
))

register('js_ie', Bundle(
    'src/js/ie/html5shiv.js',
    'src/js/ie/respond.js',
    'src/js/ie/placeholders.js',
    filters=('iife', 'uglifyjs',),
    output='ie.js',
))

# CKEditor:
register('js_ckeditor', Bundle(
    CKEditor.js,
    filters=('iife', 'uglifyjs',),
    output='ckeditor.js',
))

register('css_ckeditor', Bundle(
    CKEditor.css,
    filters=('pyscss', 'autoprefixer',),
    output='ckeditor.css',
))
register('css_ckeditor_gecko', Bundle(
    CKEditor.css_gecko,
    filters=('pyscss',),
    output='ckeditor_gecko.css',
))
register('css_ckeditor_ie', Bundle(
    CKEditor.css_ie,
    filters=('pyscss',),
    output='ckeditor_ie.css',
))
register('css_ckeditor_ie7', Bundle(
    CKEditor.css_ie7,
    filters=('pyscss',),
    output='ckeditor_ie7.css',
))
register('css_ckeditor_ie8', Bundle(
    CKEditor.css_ie8,
    filters=('pyscss',),
    output='ckeditor_ie8.css',
))
register('css_ckeditor_iequirks', Bundle(
    CKEditor.css_iequirks,
    filters=('pyscss',),
    output='ckeditor_iequirks.css',
))
register('css_ckeditor_opera', Bundle(
    CKEditor.css_opera,
    filters=('pyscss',),
    output='ckeditor_opera.css',
))
