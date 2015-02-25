# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from dfw.utils import json
from django.http import HttpResponse
from django.utils.translation import ugettext
from django.contrib import messages


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
        if self.request.is_ajax():
            # The save in the parent form_valid method is not used, because we
            # don't want to redirect on success
            self.object = form.save()
            dictionary = self.get_form_valid_ajax_dictionary(form)
            return self.render_to_json_response(dictionary)
        response = super(AjaxableResponseMixin, self).form_valid(form)
        return response

    def form_invalid(self, form):
        if '__all__' not in form.errors:
            form.errors['__all__'] = [ugettext("There was an error in the form. Please, check the fields marked in red.")]

        import pprint; pprint.pprint(form.errors)
        response = super(AjaxableResponseMixin, self).form_invalid(form)
        if self.request.is_ajax():
            dictionary = self.get_form_invalid_ajax_dictionary(form)
            return self.render_to_json_response(dictionary, status=self.invalid_ajax_status)
        return response


class CreateMessageMixin(object):
    valid_message = ugettext("<strong>Success!</strong> The object was successfully created.")
    invalid_message = ugettext("<strong>Failed!</strong> The object could not be created. Please correct the indicated errors and try again.")

    def get_valid_message(self):
        return self.valid_message

    def get_invalid_message(self):
        return self.invalid_message

    def form_valid(self, form):
        res = super(CreateMessageMixin, self).form_valid(form)
        if not self.request.is_ajax():
            messages.success(self.request, self.get_valid_message())
        return res

    def form_invalid(self, form):
        res = super(CreateMessageMixin, self).form_invalid(form)
        if not self.request.is_ajax():
            messages.error(self.request, self.get_invalid_message())
        return res


class UpdateMessageMixin(CreateMessageMixin):
    valid_message = ugettext("<strong>Success!</strong> The object was successfully updated.")
    invalid_message = ugettext("<strong>Failed!</strong> The object could not be updated. Please correct the indicated errors and try again.")
