# -*- coding: utf-8 -*-
# Copyright (c) 2012-2014 German M. Bravo (Kronuz)

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Nested Forms
============

* **Plain Nested Forms:**
  :class:`FormField` and
  :class:`FormSetField`
  *field classes to be used with:*
  :class:`NestedForm`.

* **Nested Forms for Models:**
  :class:`InlineFormField` and
  :class:`InlineFormSetField`
  *field classes, to be used from with:*
  :class:`NestedModelForm` and
  :class:`NestedInlineForm`.

Nested Forms Classes
--------------------

Form classes
~~~~~~~~~~~~

.. autoclass:: NestedForm
.. autoclass:: NestedModelForm
.. autoclass:: NestedInlineForm


Formset classes
~~~~~~~~~~~~~~~

.. autoclass:: BaseNestedFormSet
.. autoclass:: BaseNestedModelFormSet
.. autoclass:: BaseNestedInlineFormSet


Form Field classes
~~~~~~~~~~~~~~~~~~

.. autoclass:: FormField
.. autoclass:: FormSetField

Inline Form Field classes
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: InlineFormField
.. autoclass:: InlineFormSetField

Model Form Field classes
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: ModelFormField
.. autoclass:: ModelFormSetField

"""

from __future__ import absolute_import, unicode_literals

import six
import warnings

from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import MergeDict
from django.http.request import QueryDict

from django.db.models import ForeignKey
from django.db.models.fields import FieldDoesNotExist
from django.forms.forms import Form
from django.forms.fields import Field, FileField
from django.forms.widgets import SubWidget
from django.forms.util import ErrorDict
from django.forms.formsets import BaseFormSet, formset_factory, ManagementForm, \
    TOTAL_FORM_COUNT, INITIAL_FORM_COUNT, MIN_NUM_FORM_COUNT, MAX_NUM_FORM_COUNT
from django.forms.models import ModelForm, BaseModelFormSet, BaseInlineFormSet, InlineForeignKeyField, \
    modelform_factory, modelformset_factory, inlineformset_factory, construct_instance, _get_foreign_key

__all__ = ('NestedForm', 'NestedModelForm', 'NestedInlineForm',
           'FormField', 'FormSetField',
           'ModelFormField', 'ModelFormSetField',
           'InlineFormField', 'InlineFormSetField',
           'BaseNestedFormSet')


def save_instance(form, instance, fields=None, fail_message='saved',
                  commit=True, exclude=None, construct=True):
    """
    Saves bound Form ``form``'s cleaned_data into model instance ``instance``.

    If commit=True, then the changes to ``instance`` will be saved to the
    database. Returns ``instance``.

    If construct=False, assume ``instance`` has already been constructed and
    just needs to be saved.

    This is almost identical to django's default ``save_instance``, except
    we add ``save_fk`` method which needs to be called before saving the
    instance in order to save those objects pointed to with a foreign key.

    """
    if construct:
        instance = construct_instance(form, instance, fields, exclude)
    opts = instance._meta
    if form.errors:
        raise ValueError("The %s could not be %s because the data didn't"
                         " validate." % (opts.object_name, fail_message))

    self_save_fk = getattr(form, 'save_fk', None)

    def save_fk():
        if self_save_fk:
            self_save_fk()

        cleaned_data = form.cleaned_data
        for f in opts.fields:
            if not isinstance(f, ForeignKey):
                continue
            if fields is not None and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if f.name in cleaned_data:
                data = cleaned_data[f.name]
                data.save()
                f.save_form_data(instance, data)

    # Wrap up the saving of m2m data as a function.
    self_save_m2m = getattr(form, 'save_m2m', None)

    def save_m2m():
        if self_save_m2m:
            self_save_m2m()

        cleaned_data = form.cleaned_data
        for f in opts.many_to_many:
            if fields is not None and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if f.name in cleaned_data:
                f.save_form_data(instance, cleaned_data[f.name])
        for f in form.fields.values():
            if isinstance(f, InlineFormSetField):
                if not f.widget.instance.pk:
                    f.widget.instance = instance
                f.widget.save()

    if commit:
        # If we are committing, save the instance and the m2m data immediately.
        save_fk()
        instance.save()
        save_m2m()
    else:
        # We're not committing. Add a method to the form to allow deferred
        # saving of m2m data.
        form.save_fk = save_fk
        form.save_m2m = save_m2m

    return instance


class SaveInstanceNestedFormMixin(object):
    def save(self, commit=True):
        """
        Saves this ``form``'s cleaned_data into model instance
        ``self.instance``.

        If commit=True, then the changes to ``instance`` will be saved to the
        database. Returns ``instance``.

        Same as django's own ``save()``, but uses our ``save_instance``.

        """
        if self.instance.pk is None:
            fail_message = 'created'
        else:
            fail_message = 'changed'
        return save_instance(self, self.instance, self._meta.fields,
                             fail_message, commit, self._meta.exclude,
                             construct=False)


class BaseNestedWidgetMixin(object):
    is_hidden = False
    needs_multipart_form = False
    is_localized = False
    is_required = False

    attrs = {}
    nested_css_class = 'nestedForm'

    def subwidgets(self, name, value, attrs=None, choices=()):
        yield SubWidget(self, name, value, attrs, choices)

    def render(self, name, value, attrs=None):
        extra_classes = set()
        if hasattr(self, 'nested_css_class'):
            extra_classes.add(self.nested_css_class)
        css_classes = ' '.join(extra_classes)
        if css_classes:
            html_class_attr = ' class="%s"' % css_classes

        return '<div' + html_class_attr + '>' + self.as_p() + '</div>'

    def id_for_label(self, id_):
        return id_

    def value_from_datadict(self, data, files, name):
        return self


class BaseNestedFormMixin(object):
    _nested_errors = None

    def __init__(self, *args, **kwargs):
        """
        __init__(self, *args, **kwargs)

        """
        super(BaseNestedFormMixin, self).__init__(*args, **kwargs)

    def has_required(self):
        return any(field.required for field in self.fields.values())

    def get_kwargs(self, **kwargs):
        """
        Nested Form method to pass parameters to child forms in FormFields

        """
        return kwargs


class NestedFormMixin(BaseNestedFormMixin, BaseNestedWidgetMixin):
    def __init__(self, data=None, files=None, *args, **kwargs):
        """
        __init__(self, *args, **kwargs)

        """
        self._kwargs = kwargs
        self._initial = kwargs.get('initial') or {}

        super(NestedFormMixin, self).__init__(data, files, *args, **kwargs)

        self.build_nested_forms(data, files)

    def build_nested_forms(self, data, files):
        for name, field in self.fields.items():
            if isinstance(field, FormFieldMixin):
                # Instantiate nested form.
                form_widget = self.get_form_widget(name, field, data, files)

                if isinstance(form_widget, BaseNestedFormSet):
                    form_widget.parent = self
                    form_widget.parent_field = field
                    for form in form_widget:
                        form.parent = form_widget
                        form.parent_field = field
                else:
                    form_widget.parent = self
                    form_widget.parent_field = field

                if isinstance(field, FormSetFieldMixin):
                    if field.required:
                        # Use field.required definition to setup the form widget.
                        min_num = form_widget.min_num - form_widget.initial_form_count()
                        total_form_count = form_widget.total_form_count()
                        for i in range(total_form_count * 2):
                            if min_num <= 0:
                                break
                            _form = form_widget.forms[i % total_form_count]
                            if not _form.empty_permitted:
                                continue
                            if form_widget.can_delete:
                                if form_widget._should_delete_form(_form):
                                    # Skip form if it's being deleted
                                    continue
                            if i >= total_form_count or getattr(_form, 'has_data', form.has_changed)():
                                # Giving preference to non-empty forms, mark the first
                                # ``self.min_num`` forms (not being deleted) as non-empty_permitted
                                _form.empty_permitted = False
                                min_num -= 1
                    else:
                        form_widget.validate_min = False
                else:
                    if not field.required:
                        form_widget.empty_permitted = True

                field.widget = form_widget  # Field's widget is the form instance

    def clear_errors(self):
        self._errors = {}
        self.cleaned_data = {}
        for name, field in self.fields.items():
            if hasattr(field.widget, 'clear_errors'):
                field.widget.clear_errors()

    def add_errors(self, *errors):
        for name, field in self.fields.items():
            _errors = []
            for e in errors:
                if name in e:
                    _errors.append(e[name])
            if hasattr(field.widget, 'add_errors'):
                field.widget.add_errors(*_errors)
            elif _errors:
                if self._errors is None:
                    self._errors = {}
                for e in _errors:
                    self._errors.setdefault(name, self.error_class()).extend(e)

    def get_form_widget(self, name, field, data, files):
        kwargs = self._get_kwargs(name, field)
        return field.form(self, name, data, files, **kwargs)

    def full_clean(self):
        """
        Cleans all of self.data and populates self._errors and
        self.cleaned_data.
        """
        self._errors = ErrorDict()
        if not self.is_bound:  # Stop further processing.
            return
        self.cleaned_data = {}
        # If the form is permitted to be empty, and none of the form data has
        # changed from the initial data, short circuit any validation.
        if self.empty_permitted and not self.has_data():
            return
        self._clean_fields()
        self._clean_form()
        self._post_clean()

    def _clean_fields(self):
        if not self.has_data():
            parent = self
            while parent:
                current = parent
                parent = getattr(current, 'parent', None)
                if parent and not current.parent_field.required or not current.has_required():
                    # If there's no data, and any parent is not required, pass.
                    return
                elif parent and parent.has_data():
                    break

        for name, field in self.fields.items():
            # value_from_datadict() gets the data from the data dictionaries.
            # Each widget type knows how to retrieve its own data, because some
            # widgets split data over several HTML fields.
            value = field.widget.value_from_datadict(self.data, self.files, self.add_prefix(name))
            try:
                if isinstance(field, FileField):
                    initial = self.initial.get(name, field.initial)
                    value = field.clean(value, initial)
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value
                if hasattr(self, 'clean_%s' % name):
                    value = getattr(self, 'clean_%s' % name)()
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self._errors[name] = self.error_class(e.messages)
                if name in self.cleaned_data:
                    del self.cleaned_data[name]

    ############################################################################
    # Django's BaseForm should have something ``like has_data()``
    # to check whether a form is "empty" or not.
    _filled_data = None

    def has_data(self):
        """
        Returns True if data differs from initial.
        """
        return bool(self.filled_data)

    @property
    def filled_data(self):
        if self._filled_data is None:
            self._filled_data = []
            # XXX: For now we're asking the individual widgets whether or not the
            # data has changed. It would probably be more efficient to hash the
            # initial data, store it in a hidden field, and compare a hash of the
            # submitted data, but we'd need a way to easily get the string value
            # for a given field. Right now, that logic is embedded in the render
            # method of each widget.
            for name, field in self.fields.items():
                prefixed_name = self.add_prefix(name)
                data_value = field.widget.value_from_datadict(self.data, self.files, prefixed_name)
                if not field.show_hidden_initial:
                    initial_value = getattr(self, '_initial', self.initial).get(name, field.initial)
                    if callable(initial_value):
                        initial_value = initial_value()
                else:
                    initial_prefixed_name = self.add_initial_prefix(name)
                    hidden_widget = field.hidden_widget()
                    try:
                        initial_value = field.to_python(hidden_widget.value_from_datadict(
                            self.data, self.files, initial_prefixed_name))
                    except ValidationError:
                        # Always assume data has changed if validation fails.
                        self._filled_data.append(name)
                        continue
                if hasattr(field.widget, '_has_data'):
                    warnings.warn("The _has_data method on widgets is deprecated,"
                        " define it at field level instead.",
                        PendingDeprecationWarning, stacklevel=2)
                    if field.widget._has_data(initial_value, data_value):
                        self._filled_data.append(name)
                elif getattr(field, '_has_data', field._has_changed)(initial_value, data_value):
                    self._filled_data.append(name)
        return self._filled_data
    ############################################################################

    def _get_kwargs(self, name, field):
        kwargs = self.get_kwargs(**self._kwargs)

        # Cleanup kwargs (for nested forms to use the cleaned up version)
        kwargs.pop('initial', None)
        kwargs.pop('empty_permitted', None)

        # Add a prefix to the nested form.
        if self.prefix:
            prefix = '%s-%s' % (self.prefix, name)
        else:
            prefix = name
        kwargs['prefix'] = prefix

        if self._initial:
            kwargs['initial'] = self._initial.get(name)

        return kwargs

    # Helper properties for debugging:

    @property
    def nested_errors(self):
        if self._nested_errors is not None:
            return self._nested_errors
        self._nested_errors = dict(self.errors)
        for name, field in self.fields.items():
            if hasattr(field.widget, 'nested_errors'):
                errors = field.widget.nested_errors
                if isinstance(errors, dict):
                    errors = dict(errors)
                if errors:
                    self._nested_errors[name] = errors
        return self._nested_errors


class NestedForm(NestedFormMixin, Form):
    """
    This is the base class for all forms that are nested forms or **have**
    any nested form fields.

    Example:

    .. code-block:: python

        class AddressForm(NestedForm):
            street1 = forms.CharField(max_length=200)
            street2 = forms.CharField(max_length=200, required=False)
            number = forms.IntegerField(required=False)
            country = forms.CharField(max_length=200, required=False)
            zipcode = forms.CharField(max_length=5)

        class PersonForm(NestedForm):
            name = forms.CharField(max_length=100)
            last_name = forms.CharField(max_length=100)
            address = FormField(AddressForm, required=False)

    """
    pass


class NestedModelForm(NestedFormMixin, SaveInstanceNestedFormMixin, ModelForm):
    """
    Model forms that are to be included as part of a parent nested form
    through the use of :class:`ModelFormField` should inherit from this class.

    Example:

    .. code-block:: python

        class TestForm(NestedModelForm):
            cheese = InlineFormField(Cheese)
            milk = InlineFormField(Milk)

            class Meta:
                model = Recipe

    """
    def __init__(self, data=None, files=None, *args, **kwargs):
        """
        __init__(self, *args, **kwargs)

        """
        self._instance = kwargs.get('instance')

        super(NestedModelForm, self).__init__(data, files, *args, **kwargs)

    def _get_kwargs(self, name, field):
        kwargs = super(NestedModelForm, self)._get_kwargs(name, field)

        # Cleanup kwargs (for nested forms to use the cleaned up version)
        kwargs.pop('instance', None)

        if self._instance is not None:
            if isinstance(field, InlineFormField):
                try:
                    model = self._meta.model
                    f = model._meta.get_field_by_name(name)[0]
                    # Try getting the child instance. If the foreign key has a
                    # an ID saved, or if it has a cached version, get it:
                    if getattr(self._instance, f.attname) or \
                       getattr(self._instance, f.get_cache_name(), None):
                        kwargs['instance'] = getattr(self._instance, name)
                except FieldDoesNotExist:
                    pass
            elif isinstance(field, InlineFormSetField):
                kwargs['instance'] = self._instance  # pass instance as-is

        return kwargs


class NestedInlineForm(NestedModelForm):
    """
    This is a specialization of a :class:`NestedModelForm` which also adds a foreign
    key to the children using a :class:`InlineForeignKeyField` in the form.

    Used by :class:`InlineFormField` if no ``form`` parameter is explicitly
    passed.

    Example:

    .. code-block:: python

        class CheeseForm(NestedInlineForm):
            class Meta:
                model = Cheese

        class TestForm(NestedModelForm):
            cheese = InlineFormField(Cheese, form=CheeseForm)
            milk = InlineFormField(Milk)

            class Meta:
                model = Recipe

    """
    def __init__(self, data=None, files=None, *args, **kwargs):
        """
        __init__(self, *args, **kwargs)

        """
        super(NestedInlineForm, self).__init__(data, files, *args, **kwargs)

        name = self.fk.rel.field_name
        kwargs = {'pk_field': True}

        self.fields[name] = InlineForeignKeyField(self.instance, **kwargs)

        # Add the generated field to self._meta.fields if it's defined to make
        # sure validation isn't skipped on that field.
        if self._meta.fields:
            if isinstance(self._meta.fields, tuple):
                self._meta.fields = list(self._meta.fields)
            self._meta.fields.append(self.fk.name)


class BaseNestedFormSetMixin(BaseNestedFormMixin, BaseNestedWidgetMixin):
    def _construct_form(self, i, **kwargs):
        kwargs = self.get_kwargs(**kwargs)
        form = super(BaseNestedFormSetMixin, self)._construct_form(i, **kwargs)
        form.__class__.inside_formset = True
        return form

    def clear_errors(self):
        for form in self.forms:
            if hasattr(form, 'clear_errors'):
                form.clear_errors()
            else:
                form._errors = {}
                form.cleaned_data = {}

    def add_errors(self, *errors):
        for idx, form in enumerate(self.forms):
            if hasattr(form, 'add_errors'):
                _errors = []
                for e in errors:
                    try:
                        _errors.append(e[idx])
                    except IndexError:
                        pass
                if _errors:
                    form.add_errors(*_errors)

    def has_required(self):
        return self.min_num != 0

    @property
    def nested_errors(self):
        if self._nested_errors is not None:
            return self._nested_errors
        self._nested_errors = []
        has_errors = False
        for form in self.forms:
            if hasattr(form, 'nested_errors'):
                errors = form.nested_errors
                if isinstance(errors, dict):
                    errors = dict(errors)
            else:
                errors = dict(form.errors)
            self._nested_errors.append(errors)
            if errors:
                has_errors = True
        if not has_errors:
            self._nested_errors = []
        return self._nested_errors

    ############################################################################
    # Django's BaseFormSet should have something ``like has_data()``
    # to check whether if a formset is "empty".
    def has_data(self):
        """
        Returns true if data in any form differs from initial.
        """
        return any(getattr(form, 'has_data', form.has_changed)() for form in self)
    ############################################################################


class BaseNestedFormSet(BaseNestedFormSetMixin, BaseFormSet):
    """
    Base class needed by nested formsets.

    Usually, when creating nested formsets, there's not needed to subclass
    from this and pass as a ``formset`` parameter to the nested formset field.
    Except in those cases where the formsets class needed needs further
    specialization.

    """
    pass


class BaseNestedModelFormSetMixin(BaseNestedFormSetMixin, SaveInstanceNestedFormMixin):
    def save(self, commit=True):
        """
        Same as django's own ``save()``, but also saves using ``save_fk``.

        Saves model instances for every form, adding and changing instances
        as necessary, and returns the list of instances.

        """
        if not commit:
            self.saved_forms = []

            def save_fk():
                for form in self.saved_forms:
                    form.save_fk()

            def save_m2m():
                for form in self.saved_forms:
                    form.save_m2m()

            self.save_fk = save_fk
            self.save_m2m = save_m2m
        return self.save_existing_objects(commit) + self.save_new_objects(commit)

    save.alters_data = True


class BaseNestedModelFormSet(BaseNestedModelFormSetMixin, BaseModelFormSet):
    """
    Base class needed by nested model formsets.

    Usually, when creating nested model formsets, there's not needed to subclass
    from this and pass as a ``formset`` parameter to the nested formset model field.
    Except in those cases where the formsets class needed needs further
    specialization.

    """
    pass


class BaseNestedInlineFormSet(BaseNestedModelFormSetMixin, BaseInlineFormSet):
    """
    Base class needed by nested inline formsets.

    Usually, when creating nested inline formsets, there's not needed to subclass
    from this and pass as a ``formset`` parameter to the nested formset inline field.
    Except in those cases where the formsets class needed needs further
    specialization.

    """
    pass


class InvalidWidget(NestedForm):
    _owner = None

    def __get__(self, instance, owner):
        self._owner = owner.__name__
        return self

    def id_for_label(self, id_):
        raise ImproperlyConfigured("Field %s must be declared inside a NestedForm" % self._owner)


class FormFieldMixin(object):
    widget = InvalidWidget()

    default_error_messages = {
        'required': _("This form is required."),
        'invalid': _("Invalid form."),
    }

    @property
    def errors(self):
        return self.widget.errors

    def _has_changed(self, initial, form):
        if form is None:
            return False
        return form.has_changed()

    def _has_data(self, initial, form):
        if form is None:
            return False
        return getattr(form, 'has_data', form.has_changed)()

    def _get_or_load_from_module(self, name_or_class):
        if isinstance(name_or_class, six.string_types):
            module_name, _, name_or_class = name_or_class.rpartition('.')
            module = import_module(module_name)
            form = getattr(module, name_or_class)
        else:
            form = name_or_class
        return form

    def form(self, parent, name, *args, **kwargs):
        form = self._get_or_load_from_module(self.form_name)

        if issubclass(form, NestedForm):
            _form = form
        else:
            _form = type(form.__name__ + str('NestedForm'), (NestedForm, form,), {})

        form_widget = _form(*args, **kwargs)
        return form_widget

    def validate(self, value):
        if value.has_data():
            if not value.is_valid():
                raise ValidationError(self.error_messages['invalid'], code='invalid')
        elif self.required and value.has_required():
            raise ValidationError(self.error_messages['required'], code='required')


class FormField(FormFieldMixin, Field):
    """
    .. seealso::

        :class:`InlineFormField` for inline model form fields.

    This field links a form with its parent form by creating a nested subform
    that is inserted inplace during the rendering of the HTML.

    """
    def __init__(self, form, required=True, widget=None, *args, **kwargs):
        """
        __init__(self, form, *args, **kwargs)

        :param form: A python's canonical class name or the class itself
        :param ...: The same other arguments received by django's own
            :py:class:`~django.forms.fields.Field`

        """
        self.form_name = form

        super(FormField, self).__init__(required=required, widget=widget, *args, **kwargs)


class FormSetFieldMixin(FormFieldMixin):
    def _has_changed(self, initial, formset):
        if formset is None:
            return False
        return any(form.has_changed() for form in formset)

    def _has_data(self, initial, formset):
        if formset is None:
            return False
        return any(getattr(form, 'has_data', form.has_changed)() for form in formset)


class FormSetField(FormSetFieldMixin, Field):
    """
    .. seealso::

        :class:`InlineFormSetField` for inline model formset fields.

    This field links many forms to its parent by creating a nested formset of
    subforms that is inserted inplace during the rendering of the final HTML.

    """
    def __init__(self, form, formset=BaseNestedFormSet, extra=1, can_order=False,
                 can_delete=False, max_num=None, validate_max=False,
                 min_num=None, validate_min=False,
                 required=None, widget=None, *args, **kwargs):
        """
        __init__(self, form, formset=BaseNestedFormSet, *args, **kwargs)

        :param form: A python's canonical class name or the :class:`NestedForm`
            class itself.
        :param formset: A python's canonical class name or the
            :class:`BaseNestedFormSet` class itself.
        :param ...: The same other arguments received by django's own
            :py:func:`~django.forms.models.modelformset_factory` and
            :py:class:`~django.forms.fields.Field`

        """
        self.form_name = form
        self.formset = formset
        self.extra = extra
        self.can_order = can_order
        self.can_delete = can_delete
        self.max_num = max_num
        self.validate_max = validate_max
        self.min_num = min_num
        self.validate_min = validate_min

        if self.min_num is None:
            if required or required is None:
                self.min_num = 1
                self.validate_min = True
            else:
                self.min_num = 0
                self.validate_min = False

        elif self.min_num == 0 and required:
            raise ImproperlyConfigured("min_num cannot be set to zero if the FormSetField is required")

        if required is None:
            if min_num == 0:
                required = False
            else:
                required = True

        super(FormSetField, self).__init__(required=required, widget=widget, *args, **kwargs)

    def form(self, parent, name, *args, **kwargs):
        form = self._get_or_load_from_module(self.form_name)
        formset = self._get_or_load_from_module(self.formset)

        FormSet = formset_factory(
            form,
            formset=formset,
            extra=self.extra,
            can_order=self.can_order,
            can_delete=self.can_delete,
            max_num=self.max_num,
            validate_max=self.validate_max,
            min_num=self.min_num,
            validate_min=self.validate_min,
        )

        form_widget = FormSet(*args, **kwargs)
        return form_widget


class ModelFormFieldMixin(FormFieldMixin):
    def save(self, *args, **kwargs):
        return self.widget.save(*args, **kwargs)

    def clean(self, value):
        value = Field.clean(self, value)  # Skip parent class (other than Field)
        obj = value.save(commit=False)
        return obj


class ModelFormField(ModelFormFieldMixin, Field):
    """
    .. warning::

        Note that model forms that are for models referenced by a foreign key
        in a parent model form, should use :class:`InlineFormField` instead.
        This is most likely almost always the case, so you might want
        to be using :class:`InlineFormField` instead.

    This field links a model form with its parent form by creating a nested
    model subform that is inserted inplace during the rendering of the HTML.

    """
    def __init__(self, model, form=NestedModelForm, fields=None, exclude=None,
                 formfield_callback=None, widgets=None, localized_fields=None,
                 labels=None, help_texts=None, error_messages=None,
                 instance=None,
                 required=True, widget=None, *args, **kwargs):
        """
        __init__(self, model, form=NestedModelForm, *args, **kwargs)

        :param model: A django's model class.
        :param form: A python's canonical class name or the
            :class:`NestedModelForm` class itself.
        :param ...: The same other arguments received by django's own
            :py:func:`~django.forms.models.modelform_factory` and
            :py:class:`~django.forms.fields.Field`

        """
        self.model = model
        self.form_name = form
        self.fields = fields
        self.exclude = exclude
        self.formfield_callback = formfield_callback
        self.widgets = widgets
        self.localized_fields = localized_fields
        self.labels = labels
        self.help_texts = help_texts
        self.error_messages = error_messages

        self.instance = instance

        super(ModelFormField, self).__init__(required=required, widget=widget, *args, **kwargs)

    def form(self, parent, name, *args, **kwargs):
        form = self._get_or_load_from_module(self.form_name)

        Form = modelform_factory(
            self.model,
            form=form,
            fields=self.fields,
            exclude=self.exclude,
            formfield_callback=self.formfield_callback,
            widgets=self.widgets,
            localized_fields=self.localized_fields,
            labels=self.labels,
            help_texts=self.help_texts,
            error_messages=self.error_messages,
        )

        form_widget = Form(*args, **kwargs)
        return form_widget


class InlineFormField(ModelFormFieldMixin, InlineForeignKeyField):
    """
    This field links a model form with its parent form by creating a nested
    model inline subform that is inserted inplace during the rendering of the HTML.

    The difference with :class:`ModelFormField` is that *this* field represents a
    :class:`ForeignKeyField` in a model, whilst :class:`ModelFormField` does not.

    """
    def __init__(self, model, form=NestedInlineForm, fields=None, exclude=None,
                 formfield_callback=None, widgets=None, localized_fields=None,
                 labels=None, help_texts=None, error_messages=None,
                 instance=None,
                 required=True, widget=None, *args, **kwargs):
        """
        __init__(self, model, form=NestedInlineForm, *args, **kwargs)

        """
        self.model = model
        self.form_name = form
        self.fields = fields
        self.exclude = exclude
        self.formfield_callback = formfield_callback
        self.widgets = widgets
        self.localized_fields = localized_fields
        self.labels = labels
        self.help_texts = help_texts
        self.error_messages = error_messages

        self.instance = instance

        # Skip InlineForeignKeyField, we only need some of it's functionality.
        Field.__init__(self, required=required, widget=widget, *args, **kwargs)

    def form(self, parent, name, *args, **kwargs):
        form = self._get_or_load_from_module(self.form_name)

        fk = _get_foreign_key(self.model, parent._meta.model, name)

        Form = modelform_factory(
            self.model,
            form=form,
            fields=self.fields,
            exclude=self.exclude,
            formfield_callback=self.formfield_callback,
            widgets=self.widgets,
            localized_fields=self.localized_fields,
            labels=self.labels,
            help_texts=self.help_texts,
            error_messages=self.error_messages,
        )
        Form.fk = fk

        form_widget = Form(*args, **kwargs)
        return form_widget


class ModelFormSetField(ModelFormFieldMixin, Field):
    """
    .. warning::

        Note that model formsets that are for models referenced by a foreign key
        in a parent model form, should use :class:`InlineFormSetField` instead.
        This is most likely almost always the case, so you might want to be
        using :class:`InlineFormSetField` instead.

    """
    def __init__(self, model, form=NestedModelForm, formfield_callback=None,
                 formset=BaseNestedModelFormSet, extra=1, can_delete=False,
                 can_order=False, max_num=None, validate_max=False,
                 min_num=None, validate_min=False, fields=None, exclude=None,
                 widgets=None, localized_fields=None,
                 labels=None, help_texts=None, error_messages=None,
                 instance=None,
                 required=True, widget=None, *args, **kwargs):
        """
        __init__(self, model, form=NestedModelForm, *args, **kwargs)

        """
        self.model = model
        self.form_name = form
        self.formfield_callback = formfield_callback
        self.formset = formset
        self.extra = extra
        self.can_delete = can_delete
        self.can_order = can_order
        self.max_num = max_num
        self.fields = fields
        self.exclude = exclude
        self.widgets = widgets
        self.validate_max = validate_max
        self.localized_fields = localized_fields
        self.labels = labels
        self.help_texts = help_texts
        self.error_messages = error_messages
        self.min_num = min_num
        self.validate_min = validate_min

        self.instance = instance

        super(ModelFormSetField, self).__init__(required=required, widget=widget, *args, **kwargs)

    def form(self, parent, name, *args, **kwargs):
        form = self._get_or_load_from_module(self.form_name)
        formset = self._get_or_load_from_module(self.formset)

        initial = kwargs.get('initial') or []
        extra = self.extra + len(initial)

        FormSet = modelformset_factory(
            self.model,
            form=form,
            formfield_callback=self.formfield_callback,
            formset=formset,
            extra=extra,
            can_delete=self.can_delete,
            can_order=self.can_order,
            max_num=self.max_num,
            fields=self.fields,
            exclude=self.exclude,
            widgets=self.widgets,
            validate_max=self.validate_max,
            localized_fields=self.localized_fields,
            labels=self.labels,
            help_texts=self.help_texts,
            error_messages=self.error_messages,
            min_num=self.min_num,
            validate_min=self.validate_min,
        )

        form_widget = FormSet(*args, **kwargs)
        return form_widget


class InlineFormSetField(ModelFormFieldMixin, Field):
    def __init__(self, model, form=NestedModelForm,
                 formset=BaseNestedInlineFormSet, parent_model=None, fk_name=None,
                 fields=None, exclude=None, extra=3, can_order=False,
                 can_delete=True, max_num=None, formfield_callback=None,
                 widgets=None, validate_max=False, localized_fields=None,
                 labels=None, help_texts=None, error_messages=None,
                 min_num=None, validate_min=False,
                 instance=None,
                 required=True, widget=None, *args, **kwargs):
        """
        __init__(self, model, form=NestedModelForm, formset=BaseNestedInlineFormSet, *args, **kwargs)

        """
        self.parent_model = parent_model
        self.model = model
        self.form_name = form
        self.formset = formset
        self.fk_name = fk_name
        self.fields = fields
        self.exclude = exclude
        self.extra = extra
        self.can_order = can_order
        self.can_delete = can_delete
        self.max_num = max_num
        self.formfield_callback = formfield_callback
        self.widgets = widgets
        self.validate_max = validate_max
        self.localized_fields = localized_fields
        self.labels = labels
        self.help_texts = help_texts
        self.error_messages = error_messages
        self.min_num = min_num
        self.validate_min = validate_min

        self.instance = instance

        super(InlineFormSetField, self).__init__(required=required, widget=widget, *args, **kwargs)

    def form(self, parent, name, *args, **kwargs):
        if self.parent_model is None:
            parent_model = parent._meta.model
        else:
            parent_model = self.parent_model

        form = self._get_or_load_from_module(self.form_name)
        formset = self._get_or_load_from_module(self.formset)

        FormSet = inlineformset_factory(
            parent_model,
            self.model,
            form=form,
            formset=formset,
            fk_name=self.fk_name,
            fields=self.fields,
            exclude=self.exclude,
            extra=self.extra,
            can_order=self.can_order,
            can_delete=self.can_delete,
            max_num=self.max_num,
            formfield_callback=self.formfield_callback,
            widgets=self.widgets,
            validate_max=self.validate_max,
            localized_fields=self.localized_fields,
            labels=self.labels,
            help_texts=self.help_texts,
            error_messages=self.error_messages,
            min_num=self.min_num,
            validate_min=self.validate_min,
        )

        form_widget = FormSet(*args, **kwargs)
        return form_widget


################################################################################
# The following mixins should have it's own package,
# these have little to nothing to do with nested forms:

class AutoDataFormMixin(object):
    """
    This mixin auto fills the fields using initial values (specified by each field)

    This auto filling behavior can be disabled defining ``@disable_auto_data`` in ``self.data``

    """

    def get_data(self):
        if '@disable_auto_data' in self._data:
            return self._data
        if not hasattr(self, '_data_'):
            self._data_ = self._data
            if isinstance(self._data, MergeDict):
                data = QueryDict(None, mutable=True)
                for d in self._data.dicts:
                    data._encoding = d._encoding
                    data.update(d)
                self._data = data  # Make data mutable
            elif not getattr(self._data, '_mutable', True):
                self._data_ = self._data.copy()  # Make data mutable
            for name, field in self.fields.items():
                initial_value = None
                prefixed_name = self.add_prefix(name)
                data_value = field.widget.value_from_datadict(self._data_, self.files, prefixed_name)
                if data_value is None:
                    if not field.show_hidden_initial:
                        initial_value = self.initial.get(name, field.initial)
                        if callable(initial_value):
                            initial_value = initial_value()
                    else:
                        initial_prefixed_name = self.add_initial_prefix(name)
                        hidden_widget = field.hidden_widget()
                        try:
                            initial_value = field.to_python(hidden_widget.value_from_datadict(
                                self.data, self.files, initial_prefixed_name))
                        except ValidationError:
                            # Always assume data has changed if validation fails.
                            self._changed_data.append(name)
                            continue
                    if callable(initial_value):
                        initial_value = initial_value()
                    if initial_value is not None:
                        self._data_[prefixed_name] = initial_value
        return self._data_

    def set_data(self, value):
        self._data = value
        if hasattr(self, '_data_'):
            del self._data_
        return self._data

    data = property(get_data, set_data)


class AutoManagementFormMixin(object):
    def __init__(self, *args, **kwargs):
        super(AutoManagementFormMixin, self).__init__(*args, **kwargs)

        if self.is_bound:
            if isinstance(self.data, MergeDict):
                data = QueryDict(None, mutable=True)
                for d in self.data.dicts:
                    data._encoding = d._encoding
                    data.update(d)
                self.data = data  # Make data mutable
            elif not getattr(self.data, '_mutable', True):
                self.data = self.data.copy()  # Make data mutable

    @property
    def management_form(self):
        """
        Returns the ManagementForm instance for this FormSet.

        Automatically generates a default ManagementForm if it doesn't exist.

        """
        if self.is_bound:
            form = ManagementForm(self.data, auto_id=self.auto_id, prefix=self.prefix)
            if not form.is_valid():
                self.is_bound = False
                data = {
                    self.prefix + '-' + TOTAL_FORM_COUNT: self.total_form_count(),
                    self.prefix + '-' + INITIAL_FORM_COUNT: self.initial_form_count(),
                    self.prefix + '-' + MIN_NUM_FORM_COUNT: self.min_num,
                    self.prefix + '-' + MAX_NUM_FORM_COUNT: self.max_num,
                }
                self.data.update(data)

                self.is_bound = True
                form = ManagementForm(self.data, auto_id=self.auto_id, prefix=self.prefix)
                if not form.is_valid():
                    raise ValidationError(
                        _("ManagementForm data is missing or has been tampered with"),
                        code='missing_management_form',
                    )
        else:
            form = ManagementForm(auto_id=self.auto_id, prefix=self.prefix, initial={
                TOTAL_FORM_COUNT: self.total_form_count(),
                INITIAL_FORM_COUNT: self.initial_form_count(),
                MIN_NUM_FORM_COUNT: self.min_num,
                MAX_NUM_FORM_COUNT: self.max_num
            })
        return form
