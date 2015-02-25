# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from django.utils import six
from django.forms.forms import BaseForm
from django.forms.formsets import BaseFormSet

from dfw.utils.datastructures import SortedDictIndex


class Unretrieved(six.text_type):
    pass


class FormFieldDict(dict):
    _unretrieved = Unretrieved()

    def __init__(self, form, *args, **kwargs):
        load = kwargs.pop('_load', None)
        dict.__init__(self, *args, **kwargs)
        self['__form_%d' % id(form)] = True
        self.form = form
        self.fields = {}
        data = self.form.data
        prefix = self.form.prefix or ''
        if prefix:
            prefix += '-'
            conceptos_data = SortedDictIndex(data)
            data = dict(conceptos_data.range(prefix, new_prefix=''))
        for field_name in data:
            field_name, _, is_branch = field_name.partition('-')
            if not is_branch:
                self.fields[field_name] = prefix + field_name
        for field_name in self.form.initial:
            self.fields[field_name] = field_name
        for field_name in self.form.fields:
            self.fields[field_name] = field_name
        if load is not None:
            self._populate(load)

    def _populate(self, load=False):
        _populated = getattr(self, '_populated', None)
        if load:
            if _populated is not True:
                for field_name in self.fields:
                    self.__getitem__(field_name)
                self._populated = True
        elif _populated is None:
            for field_name in self.fields:
                self.setdefault(field_name, FormFieldDict._unretrieved)
            self._populated = False

    def __getitem__(self, field_name):
        try:
            value = dict.__getitem__(self, field_name)
            if value is FormFieldDict._unretrieved:
                raise KeyError
        except KeyError:
            try:
                bound_field = self.form[field_name]
                value = bound_field.value() or ""
            except KeyError:
                try:
                    value = self.form.data[self.fields[field_name]]
                except KeyError:
                    value = self.form.initial[field_name]
            # FIXME: These FormFieldDict() should not be needed to be loaded (should be lazy)?:
            if isinstance(value, BaseForm):
                value = FormFieldDict(value, _load=True)
            elif isinstance(value, BaseFormSet):
                value = [FormFieldDict(form, _load=True) for form in value]
            self[field_name] = value
        return value

    def __contains__(self, key):
        self._populate()
        return dict.__contains__(self, key)
    has_key = __contains__

    def __len__(self):
        self._populate()
        return dict.__len__(self)

    def __iter__(self):
        self._populate()
        return iter(dict.__iter__(self))

    def _iteritems(self):
        for key in iter(self):
            yield key, self[key]

    def _iterkeys(self):
        for key in iter(self):
            yield key

    def _itervalues(self):
        for key in iter(self):
            yield self[key]

    if six.PY3:
        items = _iteritems
        keys = _iterkeys
        values = _itervalues
    else:
        iteritems = _iteritems
        iterkeys = _iterkeys
        itervalues = _itervalues

        def items(self):
            self._populate(True)
            return dict.items(self)

        def keys(self):
            self._populate()
            return dict.keys(self)

        def values(self):
            self._populate(True)
            return dict.values(self)

    def copy(self):
        return self.__class__(self.form, self)

    def __repr__(self):
        self._populate(True)
        return dict.__repr__(self)

    def get_dict(self):
        self._populate(True)
        return self
