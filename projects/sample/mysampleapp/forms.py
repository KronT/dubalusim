# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals  # >> important to ease the migration to python3

from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field
from crispy_forms.bootstrap import FormActions, StrictButton

from .models import MySampleModel


class MySampleFormHelper(FormHelper):  # >> Preferred helper style, but it could be implemented as a property when some display information depends on the context of the instance
    layout = Layout(
        Div(
            Field('name', placeholder=_("Name")),
            css_class='col-sm-4'
        ),
        Div(
            Field('gender'),
            css_class='col-sm-4'
        ),
        Div(
            Field('age', placeholder=_("Age")),
            css_class='col-sm-4'
        ),
        FormActions(
            StrictButton(
                _("Save"),
                type='submit',
                css_class='btn btn-primary ladda-button',
                data_style='expand-left',
            ),
            css_class='add-new text-right',
        ),
        css_class='row',
        form_show_labels=False,
    )


class MySampleForm(ModelForm):
    class Meta:
        model = MySampleModel

    helper = MySampleFormHelper()
