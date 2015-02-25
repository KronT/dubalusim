# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import json

from django.forms.models import BaseModelForm
from django.forms.formsets import BaseFormSet
from django.utils.importlib import import_module
from django.http import Http404, HttpResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core import signing
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from nestedforms.utils import expand_nested_errors

from .utils import decode_params


class LazyFormView(object):
    prefix = '__fp__'
    count = '__fc__'

    def __init__(self, request, params):
        self.request = request
        self.params = params

    def _get_form(self, **kwargs):
        """
        This function is a form instance factory.

        Recursively figures out the form class and returns the form instance

        """
        data = kwargs.get('data', self.request.REQUEST) or None
        prefix = kwargs.get('prefix', self.prefix)
        form_class = kwargs.get('form_class', self.form_class)
        field_name = kwargs.get('field_name', self.field_name)
        form_instance = kwargs.get('form_instance')

        if issubclass(form_class, BaseFormSet):
            if not form_instance:
                form_instance = form_class(data, prefix=prefix)
            prefix = form_instance.empty_form.prefix.replace('__prefix__', '__fc__')
            form_class = form_instance.empty_form.__class__
            form_instance = None

        if not field_name and self.pk and issubclass(form_class, BaseModelForm):
            model_class = form_class._meta.model
            try:
                instance = model_class.objects.get(pk=self.pk)
            except model_class.DoesNotExist:
                if field_name is None:
                    raise
                instance = None
            form_instance = form_class(data, instance=instance, prefix=prefix)

        elif not form_instance:
            form_instance = form_class(data, prefix=prefix)

        if field_name:
            try:
                field = form_instance.fields[field_name]
            except KeyError:
                raise ImportError

            if not hasattr(field, 'form'):
                raise ImportError

            form_instance = field.widget
            form_instance = self._get_form(
                data=data,
                prefix=prefix,
                form_class=form_instance.__class__,
                form_instance=form_instance,
                field_name=None)

        return form_instance

    def get_form(self):
        form = self._get_form()
        if self.request.method != 'POST':
            if hasattr(form, 'clear_errors'):
                form.clear_errors()
            else:
                form._errors = {}
                form.cleaned_data = {}
        return form

    def populate(self):
        try:
            form_class, field_name, helper, pk, extra_params = decode_params(self.request.entity and self.request.entity.pk, self.params)
        except ImportError:
            raise Http404
        except signing.BadSignature:
            raise PermissionDenied

        module_name, _, form_name = form_class.rpartition('.')
        module = import_module(module_name)
        try:
            form_class = getattr(module, form_name)
        except AttributeError:
            raise ImportError

        self._form_class = form_class
        self._field_name = field_name
        self._helper = helper
        self._pk = pk
        self._extra_params = extra_params

    # Params

    def get_form_class(self):
        if not hasattr(self, '_form_class'):
            self.populate()
        return self._form_class

    @property
    def form_class(self):
        return self.get_form_class()

    def get_field_name(self):
        if not hasattr(self, '_field_name'):
            self.populate()
        return self._field_name

    @property
    def field_name(self):
        return self.get_field_name()

    def get_helper(self):
        if not hasattr(self, '_helper'):
            self.populate()
        return self._helper

    @property
    def helper(self):
        return self.get_helper()

    def get_pk(self):
        if not hasattr(self, '_pk'):
            self.populate()
        return self._pk

    @property
    def pk(self):
        return self.get_pk()

    def get_extra_params(self):
        if not hasattr(self, '_extra_params'):
            self.populate()
        return self._extra_params

    @property
    def extra_params(self):
        return self.get_extra_params()

    # Views

    def load(self, template_name='lazyforms/load.html', context_instance=None):
        return render_to_response(template_name, {
            'helper': self.helper,
            'form': self.get_form(),
        }, context_instance=RequestContext(self.request) if context_instance is None else context_instance)

    def validate(self):
        errors = expand_nested_errors(self.get_form().nested_errors, self.prefix)

        return HttpResponse(json.dumps(errors), content_type='text/json')


@require_http_methods(['GET'])
@never_cache
def load(request, params, template_name='lazyforms/load.html', context_instance=None):
    return LazyFormView(request, params).load(template_name, context_instance)


def validate(request, params):
    return LazyFormView(request, params).validate()


from django.views.generic import UpdateView
from django.utils.translation import ugettext
from django.template.loader import render_to_string


class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)
    """
    invalid_ajax_status = 400

    def render_to_json_response(self, context, **response_kwargs):
        data = json.dumps(context)
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)

    def get_form_valid_ajax_dictionary(self, form):
        return {
            'pk': self.object.pk,
        }

    def get_form_invalid_ajax_dictionary(self, form):
        return form.errors

    def form_valid(self, form):
        self._is_valid = True
        if self.request.is_ajax():
            # The save in the parent form_valid method is not used, because we
            # don't want to redirect on success
            self.object = form.save()
            dictionary = self.get_form_valid_ajax_dictionary(form)
            return self.render_to_json_response(dictionary)
        response = super(AjaxableResponseMixin, self).form_valid(form)
        return response

    def form_invalid(self, form):
        self._is_valid = False

        import pprint; pprint.pprint(form.errors)
        response = super(AjaxableResponseMixin, self).form_invalid(form)
        if self.request.is_ajax():
            dictionary = self.get_form_invalid_ajax_dictionary(form)
            return self.render_to_json_response(dictionary)
        return response


class CreateMessageMixin(object):
    valid_message = ugettext("<strong>Success!</strong> The object was successfully created.")
    invalid_message = ugettext("<strong>Failed!</strong> The object could not be created. Please correct the indicated errors and try again.")

    def get_valid_message(self, form):
        if hasattr(form, 'get_valid_message'):
            vm = form.get_valid_message()
        else:
            vm = self.valid_message
        return vm

    def get_invalid_message(self, form):
        if hasattr(form, 'get_valid_message'):
            vm = form.get_invalid_message()
        else:
            vm = self.invalid_message
        return vm


class UpdateMessageMixin(CreateMessageMixin):
    valid_message = ugettext("<strong>Success!</strong> The object was successfully updated.")
    invalid_message = ugettext("<strong>Failed!</strong> The object could not be updated. Please correct the indicated errors and try again.")


class LazyInlineEditFieldView(AjaxableResponseMixin, UpdateMessageMixin, UpdateView):
    model = None
    template_name = 'lazyforms/load.html'
    detail_helper = 'loadable_detail_helper'
    edit_helper = 'edit_helper'

    def _resolve_params(self, **kwargs):
        """
        This function is a form instance factory.

        Recursively figures out the form class and returns the form instance

        """
        try:
            form_class, field_name, helper, pk, extra_params = decode_params(self.request.entity and self.request.entity.pk, self.kwargs['params'])
        except ImportError:
            raise Http404
        except signing.BadSignature:
            raise PermissionDenied

        module_name, _, form_name = form_class.rpartition('.')
        module = import_module(module_name)
        try:
            self._form_class = getattr(module, form_name)
        except AttributeError:
            raise ImportError

        # inject the retrieved pk so that the object can be properly created
        self.kwargs[self.pk_url_kwarg] = pk

    def get_form_class(self):
        return self._form_class

    def get_queryset(self):
        """
        Get the queryset to look an object up against. May not be called if
        `get_object` is overridden.
        """
        if self.model is not None:
            model = self.model
        else:
            model = self.get_form_class()._meta.model

        return model._default_manager.all()

    def get_helper(self):
        if self.request.method == 'POST' and self._is_valid:
            return self.detail_helper
        return self.edit_helper

    def dispatch(self, request, *args, **kwargs):
        self._resolve_params()
        if not self.can_edit_item():
            raise PermissionDenied
        return super(LazyInlineEditFieldView, self).dispatch(request, *args, **kwargs)

    def get_form_valid_ajax_dictionary(self, form):
        context = self.get_context_data(form=form)
        return {
            'status': 'OK',
            'message': self.get_valid_message(form),
            'settimer': True,
            'data': render_to_string(
                self.get_template_names(),
                context,
                context_instance=RequestContext(self.request)
            ),
        }

    def get_form_invalid_ajax_dictionary(self, form):
        context = self.get_context_data(form=form)
        return {
            'status': 'ERR',
            'message': self.get_invalid_message(form),
            'settimer': True,
            'data': render_to_string(
                self.get_template_names(),
                context,
                context_instance=RequestContext(self.request)
            ),
        }

    def get_context_data(self, **kwargs):
        context = super(LazyInlineEditFieldView, self).get_context_data(**kwargs)
        context.update(dict(
            helper=self.get_helper(),
        ))
        return context

    def can_edit_item(self):  # FIXME
        # raise NotImplementedError("can_edit_item method hasn't been implemented")
        return True

inline_edit = login_required(LazyInlineEditFieldView.as_view())
