# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.utils.translation import ugettext_lazy as _

from django.forms import DateField, DateTimeField, IntegerField, DecimalField, HiddenInput
from django.forms.forms import Form
from django.forms.formsets import BaseFormSet

from crispy_forms.layout import Layout, Field, Submit
from crispy_extra_fields.layout import DynamicFormSet, DynamicFormSetForm, DynamicFormSetLoader, DynamicFormSetDelete, Flow

from collections import OrderedDict

import types


def create_form_helper(form, basehelper, helper=None, inside_formset=False, **extra_fields):
    if not isinstance(form, types.InstanceType):
        form = form()
    if basehelper is None:
        raise TypeError("basehelper is None")
    fields = OrderedDict()
    min_num_cols = getattr(form, '_widget_min_num_cols', 3)
    if not inside_formset:
        inside_formset = getattr(form, 'inside_formset', False)
    for fieldname, field in form.fields.items():
        if hasattr(field, 'formset'):
            fields[fieldname] = Flow.Item(DynamicFormSet(DynamicFormSetLoader(
                fieldname,
                text=_("Add %s") % fieldname,
                icon_class='fa fa-plus-circle icon-green', helper=helper),
                fieldname,
                field_name=fieldname,
                css_class='col-sm-12 col-md-12'))
        elif hasattr(field, 'form_name'):
            fields[fieldname] = Flow.Item(Field(fieldname), 12)
        elif isinstance(field.widget, HiddenInput):
            fields[fieldname] = Flow.Item(fieldname, identity=True)
        else:
            if isinstance(field, DateField):
                fields[fieldname] = Flow.Item(Field(fieldname, data_provide='datepicker-inline'), 12, 6, min_num_cols)
            elif isinstance(field, DateTimeField):
                fields[fieldname] = Flow.Item(Field(fieldname, data_provide='datepicker-inline'), 12, 6, min_num_cols)
            elif isinstance(field, (DecimalField, IntegerField)):
                fields[fieldname] = Flow.Item(fieldname, 12, 6, min_num_cols)
            else:
                rawsize = getattr(field, 'maxLength', getattr(field, 'max_length', 0))

                if rawsize > 0:
                    size = min(12, 1 + rawsize / 8)
                    size = (12, max(min_num_cols, size))
                else:
                    size = (12, 6, min_num_cols)
                fields[fieldname] = Flow.Item(fieldname, *size)

    field_list = tuple(fields.keys())
    if inside_formset:
        def layout(cls):
            items = [getattr(cls, attr) for attr in field_list]
            items.append(Flow.Item(DynamicFormSetDelete(delete_icon_class='fa fa-minus-circle icon-red',
                                                        delete_div_class='col-icon'), 1, fixedcols=True))
            return Layout(DynamicFormSetForm(Flow(*items,
                                                  justify=cls.flow_justify,
                                                  row=cls.flow_row)),
                          form_show_labels=cls.form_show_labels,
                          form_tag=cls.form_tag,
                          disable_csrf=cls.disable_csrf)
    else:
        def layout(cls):
            items = [getattr(cls, attr) for attr in field_list]
            layout = Layout(Flow(*items,
                                justify=cls.flow_justify,
                                row=cls.flow_row),
                            form_show_labels=cls.form_show_labels,
                            form_tag=cls.form_tag,
                            disable_csrf=cls.disable_csrf)
            for item in items:
                print(str(item))
            return layout

    fields['get_layout'] = classmethod(layout)
    extra_fields.update(fields)
    extra_fields.setdefault('form_show_labels', True)
    extra_fields.setdefault('form_tag', True)
    extra_fields.setdefault('disable_csrf', True)
    extra_fields.setdefault('flow_justify', True)
    extra_fields.setdefault('flow_row', 0)

    klass = type(form.__class__.__name__, (basehelper,), extra_fields)
    layout = klass.layout = klass.get_layout()
    if layout.form_tag:
        layout.add_input(Submit('submit', _("Submit")))

    return klass


def create_list_form_helper(forms, basehelper=None, helper=None):
    _inside_formset = {}
    for _, form in forms:
        for field in form.fields.values():
            if hasattr(field, 'formset', None):
                if isinstance(field.form_name, types.StringTypes):
                    classname = field.form_name
                else:
                    classname = field.form_name.__name__
                _inside_formset[classname] = True

    klasses = []
    for classname, form in forms:
        klass = create_form_helper(form, basehelper=basehelper, helper=helper,
                                   inside_formset=_inside_formset.get(classname, False))
        klasses.append((classname, klass))

    return dict(klasses)


def create_mod_form_helper(mod, basehelper=None, helper=None):
    forms = []
    for classname in dir(mod):
        attr = getattr(mod, classname)
        try:
            if not issubclass(attr, (Form, BaseFormSet)):
                continue
        except TypeError:
            continue
        form = attr(prefix='')
        forms.append((classname, form))
