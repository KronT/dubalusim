# -*- coding: utf-8 -*-
from django.conf import settings
from django.forms.formsets import BaseFormSet
from django.template import Context
from django.template.loader import get_template
from django.utils import six

from django import template
register = template.Library()

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.utils import KeepContext

# We import the filters, so they are available when doing load crispy_forms_tags
from crispy_forms.templatetags.crispy_forms_filters import *  # NOQA

TEMPLATE_PACK = getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')
ALLOWED_TEMPLATE_PACKS = getattr(settings, 'CRISPY_ALLOWED_TEMPLATE_PACKS', ('bootstrap', 'uni_form'))


class ForLoopSimulator(object):
    """
    Simulates a forloop tag, precisely::

        {% for form in formset.forms %}

    If `{% crispy %}` is rendering a formset with a helper, We inject a `ForLoopSimulator` object
    in the context as `forloop` so that formset forms can do things like::

        Fieldset("Item {{ forloop.counter }}", [...])
        HTML("{% if forloop.first %}First form text{% endif %}"
    """
    def __init__(self, formset):
        self.len_values = len(formset.forms)

        # Shortcuts for current loop iteration number.
        self.counter = 1
        self.counter0 = 0
        # Reverse counter iteration numbers.
        self.revcounter = self.len_values
        self.revcounter0 = self.len_values - 1
        # Boolean values designating first and last times through loop.
        self.first = True
        self.last = (0 == self.len_values - 1)

    def iterate(self):
        """
        Updates values as if we had iterated over the for
        """
        self.counter += 1
        self.counter0 += 1
        self.revcounter -= 1
        self.revcounter0 -= 1
        self.first = False
        self.last = (self.revcounter0 == self.len_values - 1)


def get_response_dict(context, helper, layout, is_formset, template_pack, is_subform):
    """
    Returns a dictionary with all the parameters necessary to render the form/formset in a template.

    :param context: `django.template.Context` for the node
    :param attrs: Dictionary with the helper's attributes used for rendering the form/formset
    :param is_formset: Boolean value. If set to True, indicates we are working with a formset.

    """
    if layout is None:
        layout = Layout()
    attrs = layout.get_attributes(helper=helper, template_pack=template_pack)
    form_type = 'form'
    if is_formset:
        form_type = 'formset'

    # We take form/formset parameters from attrs if they are set, otherwise we use defaults
    response_dict = {
        'template_pack': settings.CRISPY_TEMPLATE_PACK,
        '%s_action' % form_type: attrs['attrs'].get("action", ''),
        '%s_method' % form_type: attrs.get("form_method", 'post'),
        '%s_tag' % form_type: attrs.get("form_tag", True),
        '%s_class' % form_type: attrs['attrs'].get("class", ''),
        '%s_id' % form_type: attrs['attrs'].get("id", ""),
        '%s_style' % form_type: attrs.get("form_style", None),
        'form_error_title': attrs.get("form_error_title", None),
        'formset_error_title': attrs.get("formset_error_title", None),
        'form_show_errors': attrs.get("form_show_errors", True),
        'help_text_inline': attrs.get("help_text_inline", False),
        'html5_required': attrs.get("html5_required", False),
        'form_show_labels': attrs.get("form_show_labels", True),
        'disable_csrf': attrs.get("disable_csrf", False),
        'inputs': attrs.get('inputs', []),
        'is_formset': is_formset,
        '%s_attrs' % form_type: attrs.get('attrs', ''),
        'flat_attrs': attrs.get('flat_attrs', ''),
        'error_text_inline': attrs.get('error_text_inline', True),
        'field_class': attrs.get('field_class', ''),
        'label_class': attrs.get('label_class', ''),
        'label_offset': attrs.get('label_offset', ''),
    }

    if context.get('is_subform') or is_subform:
        response_dict['%s_tag' % form_type] = False
        response_dict['disable_csrf'] = True
    else:
        response_dict['is_subform'] = True

    # Handles custom attributes added to helpers
    for attribute_name, value in attrs.items():
        if attribute_name not in response_dict:
            response_dict[attribute_name] = value

    if 'csrf_token' in context:
        response_dict['csrf_token'] = context['csrf_token']

    if 'helper' in context:
        response_dict['helper'] = context['helper']

    return response_dict


def get_render(context, form, helper, template_pack, is_subform):
    is_formset = isinstance(form, BaseFormSet)

    if helper is None:
        helper = 'helper'

    # Resolve actual helper.
    # If we have a helper we use it, for the form or the formset's forms
    actual_helper = None
    layout = None

    if isinstance(helper, FormHelper):
        actual_helper = helper

    elif isinstance(helper, six.string_types):
        helper, _, layout = helper.partition('.')
        if not helper:
            helper = 'helper'

        # If the user names the helper within the form `helper` (standard), we use it
        # This allows us to have simplified tag syntax: {% crispy form %}
        try:
            _helper = getattr(form, helper, None) or form.helper
            if _helper is not None:
                actual_helper = _helper
        except AttributeError:
            pass

        # Use formset's helper from above, if any, otherwise fallback
        # to formset's form's helper.
        if is_formset and not actual_helper:
            try:
                actual_formset = form.form()
                _helper = getattr(actual_formset, helper, None) or actual_formset.helper
                if _helper is not None:
                    actual_helper = _helper
            except AttributeError:
                pass

    if not isinstance(actual_helper, FormHelper):
        actual_helper = FormHelper(form=form)

    if not layout:
        layout = 'layout'

    # Resolve actual layout.

    actual_layout = getattr(actual_helper, layout, None) or actual_helper.layout
    # print
    # print 'form', form.__module__, repr(form)
    # print 'helper', '(%s)' % helper, actual_helper.__module__, repr(actual_helper)
    # print 'layout', '(%s)' % layout, actual_layout.__module__, repr(actual_layout)

    if actual_layout is None:
        actual_layout = actual_helper.build_default_layout(form)

    # We get the response dictionary
    response_dict = get_response_dict(context, actual_helper, actual_layout, is_formset, template_pack, is_subform)
    context.update(response_dict)

    if actual_layout:
        # FIXME: THESE CHANGE HELPER'S STATE (SHOULD NEVER DO THIS DURING RENDER):
        if is_formset:
            forloop = ForLoopSimulator(form)
            actual_helper.render_hidden_fields = True
            for _form in form:
                context.update({'forloop': forloop})
                _form.form_html = actual_layout.render_layout(_form, context, template_pack=template_pack)
                forloop.iterate()
        else:
            form.form_html = actual_layout.render_layout(form, context, template_pack=template_pack)

    # Add rendered inputs.
    if response_dict['inputs'] and response_dict['form_tag']:
        response_dict['inputs'] = [i.render(form, response_dict['form_style'], context, template_pack=template_pack) for i in response_dict['inputs']]
    else:
        response_dict['inputs'] = None

    # Add form or formset.
    if is_formset:
        response_dict['formset'] = form
    else:
        response_dict['form'] = form

    # Add template.
    _template = getattr(actual_helper, 'template', None)
    if not _template:
        if is_formset:
            _template = '%s/whole_crispy_formset.html' % template_pack
        else:
            _template = '%s/whole_crispy_form.html' % template_pack
    response_dict['template'] = _template

    return Context(response_dict)


@register.simple_tag(takes_context=True, name='crispy')
def do_crispy_form(context, form, helper=None, template_pack=TEMPLATE_PACK, is_subform=False):
    """
    You need to pass in at least the form/formset object, and can also pass in the
    optional `crispy_forms.helpers.FormHelper` object.

    helper (optional): A `crispy_forms.helper.FormHelper` object.

    Usage::

        {% include crispy_tags %}
        {% crispy form form.helper %}

    You can also provide the template pack as the third argument::

        {% crispy form form.helper 'bootstrap' %}

    If the `FormHelper` attribute is named `helper` you can simply do::

        {% crispy form %}
        {% crispy form 'bootstrap' %}
    """
    with KeepContext(context):
        c = get_render(context, form, helper, template_pack, is_subform)
        template = get_template(c['template'])
        return template.render(c)
