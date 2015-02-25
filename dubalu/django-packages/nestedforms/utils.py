# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.formsets import TOTAL_FORM_COUNT, MIN_NUM_FORM_COUNT, MAX_NUM_FORM_COUNT, INITIAL_FORM_COUNT


def initial2data(node, prefix='', data=None):
    if data is None:
        data = {}

    if isinstance(node, dict):
        for k, v in node.items():
            if prefix:
                _prefix = '%s-%s' % (prefix, k)
            else:
                _prefix = '%s' % k
            initial2data(v, _prefix, data)

    elif isinstance(node, (tuple, list)) and node and isinstance(node[0], dict):
        for i, v in enumerate(node):
            if prefix:
                _prefix = '%s-%s' % (prefix, i)
            else:
                _prefix = '%s' % i
            initial2data(v, _prefix, data)

        total_forms_name = '%s-%s' % (prefix, TOTAL_FORM_COUNT)
        if total_forms_name in data:
            del data[total_forms_name]

        min_num_forms_name = '%s-%s' % (prefix, MIN_NUM_FORM_COUNT)
        if min_num_forms_name in data:
            del data[min_num_forms_name]

        max_num_forms_name = '%s-%s' % (prefix, MAX_NUM_FORM_COUNT)
        if max_num_forms_name in data:
            del data[max_num_forms_name]

        initial_forms_name = '%s-%s' % (prefix, INITIAL_FORM_COUNT)
        if initial_forms_name in data:
            del data[initial_forms_name]

    elif prefix:
        data[prefix] = node

    else:
        data = node

    return data


def data2initial(data):
    def get_initial(initial, field, formsets, val):
        if not field:
            return val
        field_name, _, suffix = field.partition('-')
        if field_name in initial:
            if isinstance(initial[field_name], list):
                if field_name not in formsets:
                    raise ValidationError("Unknown formset")
                #get the form number
                form_num, _, suffix = suffix.partition('-')
                initial[field_name][int(form_num)] = get_initial(initial[field_name][int(form_num)] or {}, suffix, formsets, val)
            else:
                initial[field_name] = get_initial(initial.get(field_name, {}), suffix, formsets, val)
        else:
            if field_name in formsets:
                initial[field_name] = [None] * formsets[field_name]
                #get the form number
                form_num, _, suffix = suffix.partition('-')
                initial[field_name][int(form_num)] = get_initial(initial[field_name][int(form_num)] or {}, suffix, formsets, val)
            else:
                initial[field_name] = get_initial(initial.get(field_name, {}), suffix, formsets, val)
        return initial

    # extract and the management info of the existing formsets

    skip_fields = set([settings.CSRF_INPUT_NAME])

    formsets = {}
    for name, val in data.items():
        if name.endswith('-%s' % TOTAL_FORM_COUNT) or name.endswith('-%s' % MIN_NUM_FORM_COUNT) or name.endswith('-%s' % MAX_NUM_FORM_COUNT):
            prefix, _, _ = name.rpartition('-')

            if prefix in formsets:
                continue

            total_forms_name = '%s-%s' % (prefix, TOTAL_FORM_COUNT)
            min_num_forms_name = '%s-%s' % (prefix, MIN_NUM_FORM_COUNT)
            max_num_forms_name = '%s-%s' % (prefix, MAX_NUM_FORM_COUNT)
            initial_forms_name = '%s-%s' % (prefix, INITIAL_FORM_COUNT)
            skip_fields.update([total_forms_name, min_num_forms_name, max_num_forms_name, initial_forms_name])

            total_forms = int(data[total_forms_name])
            min_num_forms = int(data[min_num_forms_name])
            max_num_forms = int(data[max_num_forms_name])
            if total_forms < min_num_forms or total_forms > max_num_forms:
                raise ValidationError("Invalid number of forms",
                    code='invalid_number_of_forms')
            if total_forms:
                formsets[prefix] = total_forms

    initial = {}
    for field_name, val in sorted(data.items()):
        if not val:
            continue
        if field_name in skip_fields:
            continue
        initial.update(get_initial(initial, field_name, formsets, val))
    return initial


def expand_nested_errors(node, prefix='', errors=None):
    data = initial2data(node, prefix, errors)
    return {prefix: data}
