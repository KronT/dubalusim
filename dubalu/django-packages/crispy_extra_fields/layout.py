# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import json
import hashlib

from collections import OrderedDict

from django.forms import ModelForm
from django.core import urlresolvers
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from django.utils import six

from nestedforms.forms import FormField
from lazyforms.utils import encode_params

from crispy_forms.utils import render_field, flatatt, resolve_value, get_bound_field, flatten_list
from crispy_forms.layout import TEMPLATE_PACK, Field, Template, Renderizable, Div, HTML, Hidden, Element, Button
from crispy_forms.bootstrap import StrictButton

import types


class If(Renderizable):

    def __init__(self, expr, true_layout, false_layout=None, **kwargs):
        self.expr = expr
        self.true_layout = true_layout
        self.false_layout = false_layout

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        if callable(self.expr):
            value = self.expr(form, context)
        else:
            value = bool(self.expr)

        if value:
            return render_field(
                self.true_layout,
                form,
                form_style,
                context,
                template_pack=template_pack
            )
        else:
            return render_field(
                self.false_layout,
                form,
                form_style,
                context,
                template_pack=template_pack
            )


class AjaxSubmit(Button):
    field_classes = 'submit submitButton' if TEMPLATE_PACK == 'uni_form' else 'btn btn-primary'

    def __init__(self, name, value, url_encoder=None, data_target=None, **kwargs):
        self.url_encoder = url_encoder
        self.data_target = data_target
        super(AjaxSubmit, self).__init__(name, value, **kwargs)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = {}

        data_target = self.data_target
        if data_target:
            if isinstance(self.data_target, FieldVal):
                data_target = self.data_target._render(form, form_style, context, template_pack=template_pack)
            attrs['data-target'] = data_target

        if self.url_encoder and 'src' not in self.attrs:
            attrs['src'] = self.url_encoder(form, form_style, context)

        flat_attrs = ' '.join(filter(lambda x: x, (flatatt(self.attrs), flatatt(attrs))))

        value = self.value_template.render(context) if self.value_template else self.value
        if isinstance(value, Renderizable):
            value = value.render(form, form_style, context)

        context.update({
            'input': {
                'name': self.name,
                'id': self.id,
                'input_type': self.input_type,
                'field_classes': self.field_classes,
            },
            'value': value,
            'flat_attrs': flat_attrs,
        })
        return render_to_string(self.template, context)


def basic_param_encoder(form, form_style, context, *args, **kwargs):
    module_name = form.__module__
    form_name = form.__class__.__name__
    form_class = "%s.%s" % (module_name, form_name)

    entity = context.get('entity')
    field_name = kwargs.get('field_name')
    url_name = kwargs.get('url_name', 'lazyform-load')
    helper = kwargs.get('helper') or context.get('helper')

    if hasattr(helper, 'name'):
        helper = helper.name

    if 'pk' in kwargs:
        pk = kwargs['pk']
    else:
        instance = getattr(form, 'instance', None)
        pk = instance and instance.pk

    params = encode_params(entity and entity.pk, form_class, field_name, helper, pk, *args)

    return urlresolvers.reverse(url_name, args=(params, ))


class ListItem(Div):
    tag = 'li'


class ListDivider(ListItem):
    css_class = 'divider'


class LazyFormCustomLoader(Element):
    template = ''
    field_classes = ''
    icon_class = ''
    element_attr = 'src'

    def __init__(self, value='', *args, **kwargs):
        self.value = value
        self.icon_first = kwargs.pop('icon_first', True)
        self.url_encoder = kwargs.pop('url_encoder', basic_param_encoder)
        self.included_params = kwargs.pop('included_params', ())
        self.url_encoder_kwargs = kwargs.pop('url_encoder_kwargs', {})
        self.url_encoder_kwargs['field_name'] = kwargs.pop('field_name', None)
        if 'icon_class' in kwargs and kwargs['icon_class'] is None:
            self.icon_class = None
        else:
            self.icon_class = kwargs.pop('icon_class', self.icon_class)
        self.attrs = kwargs
        if 'css_class' in kwargs:
            if self.field_classes:
                self.field_classes += ' ' + kwargs['css_class']
            else:
                self.field_classes = kwargs['css_class']

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)
        attrs[self.element_attr] = self.url_encoder(form, form_style, context, *self.included_params, **self.url_encoder_kwargs)

        context.update({
            'form': form,
            'field_classes': self.field_classes,
            'value': self.value,
            'icon_class': self.icon_class,
            'icon_first': self.icon_first,
            'flat_attrs': flatatt(attrs),
            'tag': getattr(self, 'tag', None),
        })
        return render_to_string(self.template, context)


class LazyLoader(LazyFormCustomLoader):
    template = 'crispy_extra_fields/lazyform_loader.html'
    data_provide = 'lazy-loader'
    method = 'get'
    tag = 'button'
    element_attr = 'action'

    def __init__(self, *args, **kwargs):
        kwargs['data_provide'] = kwargs.get('data_provide', self.data_provide)
        kwargs['method'] = kwargs.get('method', self.method)
        self.tag = kwargs.pop('tag', self.tag)
        super(LazyLoader, self).__init__(*args, **kwargs)


class BaseLoadLazyForm(LazyFormCustomLoader):
    """
    An Element that represents a loader anchor or button to load forms lazily.

    :param related: id for the element that will contain the loaded form
    :param value: text that is to be used as the body for the anchor (optional)
    :param icon_class: icon class (optional)
    :param icon_first: if set, shows the icon before the text (defaults to True)
    :param url_encoder: function that encodes a 'src' attribute for the request
        to the lazy loader view. (defaults to :func:`basic_param_encoder`)

    """


class LoadLazyFormButton(BaseLoadLazyForm):
    template = 'crispy_extra_fields/load_lazyform_button.html'
    field_classes = 'lazyform_loader button' if TEMPLATE_PACK == 'uni_form' else 'lazyform_loader btn'


class LoadLazyFormAnchor(BaseLoadLazyForm):
    template = 'crispy_extra_fields/load_lazyform_anchor.html'
    field_classes = 'lazyform_loader'


class LoadLazyFormSetFormAnchor(LazyFormCustomLoader):
    template = 'crispy_extra_fields/load_lazyform_anchor.html'
    field_classes = 'add-row'
    icon_class = 'fa fa-plus-circle' if TEMPLATE_PACK != 'uni_form' else ''

    def __init__(self, field_name, *args, **kwargs):
        if 'css_id' not in kwargs:
            kwargs['css_id'] = FieldId(field_name, prefix='div_', suffix='_loader')
        if 'related' not in kwargs:
            kwargs['related'] = FieldId(field_name, prefix='div_')
        if 'prefix' not in kwargs:
            kwargs['prefix'] = FieldId(field_name, prefix='', suffix='')
        kwargs['field_name'] = field_name
        super(LoadLazyFormSetFormAnchor, self).__init__(*args, **kwargs)


class DynamicFormSetLoader(Div):
    """
    LazyFormSetFormAnchor helper (merely adds a class and a wrapper div)

    """
    tag = 'span'
    css_class = 'dynamic_formset_loader'

    def __init__(self, field_name, text='', icon_class='', icon_first=True, helper=None, **kwargs):
        fields = [
            LoadLazyFormSetFormAnchor(
                field_name,
                value=text,
                icon_class=icon_class,
                icon_first=icon_first,
                url_encoder_kwargs=dict(
                    helper=helper,
                ),
            ),
        ]
        super(DynamicFormSetLoader, self).__init__(*fields, **kwargs)


class DynamicFormSetLoaderList(Element):
    """
    Element to insert a list of loaders coming from a view ()

    :param field_name: field name (required)

    :param params_retriever: function that returns a list of tuples used by the
        template for rendering the items. Each tuple contains the parameters
        that will be passed to the `url_encoder` function: (label, parameter, ...) (required)
    :param params_retriever_kwargs: arguments to pass to the retriever function.

    :param url_encoder: function that encodes a 'src' attribute for the request
        to the lazy loader view. (defaults to :func:`basic_param_encoder`)
    :param url_encoder_kwargs:

    """
    template = "crispy_extra_fields/dynamic_formset_loader_list.html"
    css_class = 'row'

    def __init__(self, field_name, params_retriever, icon_class='',
            params_retriever_kwargs={}, url_encoder_kwargs={}, **kwargs):
        if 'style' not in kwargs:
            kwargs['style'] = 'padding-bottom: 10px;'
        self.field_name = field_name
        self.template = kwargs.pop('template', self.template)
        self.params_retriever = params_retriever
        self.params_retriever_kwargs = params_retriever_kwargs
        self.url_encoder_kwargs = url_encoder_kwargs
        self.url_encoder_kwargs['field_name'] = field_name
        self.attrs = kwargs
        self.icon_class = icon_class

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):

        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        fields_dict = OrderedDict()
        url_encoder_kwargs = self.url_encoder_kwargs
        all_params = self.params_retriever(context, **self.params_retriever_kwargs)
        for _key, params in all_params.items():
            fields_dict.setdefault(_key, {})
            fields_dict[_key].setdefault('_display', params['_display'])
            fields_dict[_key].setdefault('item_list', [])
            for label, included_params, url_encoder_kwargs in params['item_list']:
                _url_encoder_kwargs = self.url_encoder_kwargs.copy()
                _url_encoder_kwargs.update(url_encoder_kwargs)
                fields_dict[_key]['item_list'].append(render_field(
                    LoadLazyFormSetFormAnchor(
                        self.field_name,
                        label,
                        included_params=included_params,
                        url_encoder_kwargs=_url_encoder_kwargs,
                        icon_class=self.icon_class,
                    ),
                    form,
                    form_style,
                    context,
                    template_pack=template_pack
                ))

        css_class = attrs.pop('class', self.css_class)

        return render_to_string(self.template, {
            'form': form,
            'css_id': self.css_id,
            'css_class': css_class,
            'flat_attrs': flatatt(attrs),
            'fields': fields_dict.items(),
        })


class LazyFormLoaderList(Element):
    """
    Element to insert a list of lazy form loaders
    """
    template = "crispy_extra_fields/dynamic_formset_loader_list.html"
    css_class = 'row'

    def __init__(self, *loaders, **kwargs):
        if 'style' not in kwargs:
            kwargs['style'] = 'padding-bottom: 10px;'
        self.loaders = loaders
        self.template = kwargs.pop('template', self.template)
        self.attrs = kwargs

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        fields = []
        for loader in self.loaders:
            fields.append(
                render_field(
                    loader,
                    form,
                    form_style,
                    context,
                    template_pack=template_pack
                )
            )

        css_class = attrs.pop('class', self.css_class)

        return render_to_string(self.template, {
            'form': form,
            'css_id': self.css_id,
            'css_class': css_class,
            'flat_attrs': flatatt(attrs),
            'fields': fields,
        })


class FileInputButton(Field):
    """
    REQUIRED ASSETS:
        fileinputbutton.scss
        fileinputbutton.js

    EXAMPLES:
        FileInputButton('file'),

        FileInputButton('file', text=_("Browse...")),

        FileInputButton('file', icon_class="fa fa-cloud-upload", type=FileInputButton.TYPE_SIMPLE_BUTTON),

        FileInputButton('file', text=_("Upload Files..."), multiple=True),
    """
    TYPE_SIMPLE_BUTTON = 'S'
    TYPE_BLOCK_BUTTON = 'B'
    TYPE_INCLUDE_TEXT_INPUT = 'I'

    template = 'crispy_extra_fields/fileinputbutton.html'
    field_classes = 'btn-file'

    def __init__(self, field, text='', icon_class='fa fa-upload',
            css_class='btn btn-primary', type=TYPE_INCLUDE_TEXT_INPUT,
            multiple=False):
        self.field = field
        self.text = text
        self.icon_class = icon_class
        self.type = type
        self.multiple = multiple
        if type == self.TYPE_SIMPLE_BUTTON:
            self.field_classes += ' ' + css_class
        elif type == self.TYPE_BLOCK_BUTTON:
            self.field_classes = ' '.join(filter(lambda x: x, ('file-input btn btn-block', css_class, self.field_classes)))
        else:
            self.field_classes = ' '.join(filter(lambda x: x, ('file-input btn', css_class, self.field_classes)))

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        return render_to_string(
            self.template,
            {
                'field': '-'.join(filter(lambda x: x, (getattr(form, 'prefix', ''), self.field))),
                'text': self.text,
                'icon_class': self.icon_class,
                'field_classes': self.field_classes,
                'multiple': self.multiple,
                'INCLUDE_TEXT_INPUT': self.type == self.TYPE_INCLUDE_TEXT_INPUT,
            },
        )


class DropFile(Field):
    css_class = 'ezdz'
    data_main_class = 'ezdz-dropzone'
    html_wrapper = '<div>%s</div>'

    def __init__(self, *args, **kwargs):
        if 'html' in kwargs:
            self.html = kwargs.pop('html')
        else:
            self.html = kwargs.get('data_text', _("Upload"))

        self.data_main_class += ' ' + kwargs.get('data_main_class', '')
        kwargs['data_main_class'] = self.data_main_class

        super(DropFile, self).__init__(*args, **kwargs)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        html = self.html
        if isinstance(html, Renderizable):
            html = html.render(form, form_style, context, template_pack=template_pack)
        context.update({
            'field_html': mark_safe(self.html_wrapper % html),
            'field_class': self.data_main_class,
        })
        return super(DropFile, self)._render(form, form_style, context, template_pack=template_pack)


class DropImageFile(DropFile):
    data_main_class = 'ezdz-dropzone image'
    accept = "image/*"

    def __init__(self, *args, **kwargs):
        if 'accept' not in kwargs:
            kwargs['accept'] = self.accept

        super(DropImageFile, self).__init__(*args, **kwargs)


class DynamicFormSet(Div):
    """
    :: field_name is a required
    """
    css_class = 'dynamic_formset'

    def __init__(self, *fields, **kwargs):
        kwargs['data_dynamic_formset'] = Json({
            'loaderId': FieldId(kwargs.pop('field_name'), prefix='div_', suffix='_loader'),
        })
        super(DynamicFormSet, self).__init__(*fields, **kwargs)


class DynamicFormSetDelete(Div):
    tag = 'span'

    def __init__(self, text='', delete_class='delete-row', delete_icon_class='fa fa-minus-circle',
            delete_div_class=None, **kwargs):
        self.text = text
        self.delete_class = delete_class
        self.delete_icon_class = delete_icon_class
        self.delete_div_class = delete_div_class
        super(DynamicFormSetDelete, self).__init__(**kwargs)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        if hasattr(form, 'parent') and hasattr(form.parent, 'can_delete') and form.parent.can_delete or 'DELETE' in form.fields:
            disable_delete_class = ''
        else:
            disable_delete_class = 'disable-delete'

        layout = [
            HTML('<a href="javascript:;" class="%(delete_class)s">'
            '<i class="%(delete_icon_class)s"></i></a>' % {
                'delete_class': ' '.join(filter(lambda x: x, (disable_delete_class, self.delete_class))),
                'delete_icon_class': self.delete_icon_class,
            }),
            Hidden("%s-DELETE" % form.prefix, ''),
        ]
        if self.delete_div_class:
            layout = Div(*layout, css_class=self.delete_div_class)
        else:
            layout = Div(*layout)
        layout.tag = self.tag

        return render_field(
            layout,
            form,
            form_style,
            context,
            template_pack=template_pack
        )


class DynamicFormSetForm(Div):
    css_class = 'dynamic_formset_form'


def get_field_dict(form, initial, prefix='', field_dict=None):
    if field_dict is None:
        field_dict = {}

    if isinstance(initial, dict):
        for field_name, _initial in initial.items():
            if prefix:
                _prefix = '%s-%s' % (prefix, field_name)
            else:
                _prefix = field_name
            if isinstance(form, ModelForm) and hasattr(form, 'instance') and hasattr(form.fields.get(field_name, None), 'form'):
                _form = form.fields[field_name].widget
                _initial = _form.initial
            elif prefix and isinstance(form.fields.get(prefix.rsplit('-', 1)[-1], None), FormField):
                _form = form.fields[prefix.rsplit('-', 1)[-1]].widget
            else:
                _form = form
            get_field_dict(_form, _initial, _prefix, field_dict)

    elif isinstance(initial, (tuple, list)) and isinstance(initial[0], dict):
        #inject the management formset chunk
        formset = form.fields[prefix.rsplit('-', 1)[-1]].widget
        field_dict.update({
            '%s-TOTAL_FORMS' % prefix: formset.management_form.initial['TOTAL_FORMS'],
            '%s-INITIAL_FORMS' % prefix: formset.management_form.initial['INITIAL_FORMS'],
            '%s-MIN_NUM_FORMS' % prefix: formset.management_form.initial['MIN_NUM_FORMS'],
            '%s-MAX_NUM_FORMS' % prefix: formset.management_form.initial['MAX_NUM_FORMS'],
        })
        for i, v in enumerate(initial):
            _prefix = '%s-%s' % (prefix, i)
            get_field_dict(formset.forms[i], v, _prefix, field_dict)

    else:
        field_dict[prefix] = initial

    return field_dict


class HiddenFields(Hidden):
    template = 'crispy_extra_fields/hiddenfields.html'

    def __init__(self, *fields, **kwargs):
        self.fields = flatten_list(fields)
        self.initial = kwargs.pop('data', None) is None
        self.attrs = kwargs
        self.flat_attrs = flatatt(self.attrs)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)
        hidden = []

        if self.initial:
            initial = {}
            for name in self.fields:
                field = get_bound_field(context, form, name)
                if not field:
                    continue
                if not hasattr(field.field, 'form'):
                    hidden.append(field.as_hidden(attrs=attrs))
                else:
                    if name in form.initial:
                        v = form.initial[name]
                        initial[name] = v
            fields = get_field_dict(form, initial, form.prefix)

        else:
            fields = {}
            for name in self.fields:
                field_name = '-'.join((form.prefix, name))
                if not hasattr(field.field, 'form'):
                    hidden.append(field.as_hidden(attrs=attrs))
                else:
                    for k, v in form.data.items():
                        if k.startswith(field_name):
                            fields[k] = v

        return render_to_string(self.template, {
            'hidden': hidden,
            'fields': fields,
            'field_classes': self.field_classes,
            'flat_attrs': self.flat_attrs,
        })


class Or(object):
    def __init__(self, *ops):
        self.ops = ops

    def __call__(self, form, context):
        return any([f(form, context) for f in self.ops])


class And(object):
    def __init__(self, *ops):
        self.ops = ops

    def __call__(self, form, context):
        return all([f(form, context) for f in self.ops])


class Not(object):
    def __init__(self, op):
        self.op = op

    def __call__(self, form, context):
        return not self.op(form, context)


class FieldList(object):
    def __init__(self, *fields, **kwargs):
        self.fields = flatten_list(fields)
        self.filter = kwargs.get('filter')


class HasValues(FieldList):
    """
    If all of the fields have a value, return True

    """
    deep = True

    def __call__(self, form, context):
        fields = self.fields or form.fields.keys()
        for name in fields:
            value = resolve_value(context, name)
            if callable(self.filter):
                value = self.filter(name, value)
            # print '\t>>>', name, repr(value)
            if not value:
                return False
        return True


class HasChanged(FieldList):
    deep = True

    def __call__(self, form, context):
        fields = self.fields or form.fields.keys()
        for name in fields:
            field = get_bound_field(context, form, name)
            if not field:
                continue
            if not self.deep and hasattr(field.field, 'form'):
                continue
            if name in field.form.changed_data:
                return True
        return False


class HasInitial(FieldList):
    """
    If all of the fields have initial data, return True

    """
    deep = True

    def __call__(self, form, context):
        fields = self.fields or form.fields.keys()
        for name in fields:
            field = get_bound_field(context, form, name)
            if not field:
                continue
            if not self.deep and hasattr(field.field, 'form'):
                continue
            _, _, name = name.rpartition('.')
            initial_value = field.form.initial.get(name, field.field.initial)
            if callable(initial_value):
                initial_value = initial_value()
            if not initial_value:
                return False
        return True


class HasData(FieldList):
    """
    If any of the fields has data, it returns True.

    """
    deep = True

    def __call__(self, form, context):
        fields = self.fields or form.fields.keys()
        for name in fields:
            field = get_bound_field(context, form, name)
            if not field:
                continue
            if not self.deep and hasattr(field.field, 'form'):
                continue
            _, _, name = name.rpartition('.')
            if name in field.form.filled_data:
                return True
        return False


class HasChangedShallow(HasChanged):
    deep = False


class HasInitialShallow(HasInitial):
    deep = False


class HasDataShallow(HasData):
    deep = False


class RawField(Field):
    """
    Renders a form field as a raw crispy field
    """
    template = "%s/layout/raw_field.html" % TEMPLATE_PACK


class PrependedAppended(Field):
    """
    Works pretty much the same way as crispy forms' ``bootstrap.PrependedAppendedText``,
    except this one can take more than one field and uses the first one to
    render the label and whole-field error and the next ones to have them
    appended as if being part of a composite field.
    """
    field_template = "%s/layout/raw_field.html" % TEMPLATE_PACK
    template = "%s/layout/prepended_appended.html" % TEMPLATE_PACK

    def __init__(self, *args, **kwargs):
        self.field = kwargs.pop('field', None)
        self.appended_text = kwargs.pop('appended_text', None)
        self.prepended_text = kwargs.pop('prepended_text', None)
        if 'active' in kwargs:
            self.active = kwargs.pop('active')

        self.input_size = None
        css_class = kwargs.get('css_class', '')
        if css_class.find('input-lg') != -1:
            self.input_size = 'input-lg'
        if css_class.find('input-sm') != -1:
            self.input_size = 'input-sm'

        super(PrependedAppended, self).__init__(*args, **kwargs)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)
        field_class = attrs.get('field-class')

        fields = []
        bound_field = None
        if self.field:
            bound_field = get_bound_field(context, form, self.field)
        for field in self.fields:
            if bound_field is None and isinstance(field, six.string_types):
                bound_field = get_bound_field(context, form, field)
            fields.append(render_field(field, form, form_style, context, template=self.field_template, attrs=attrs, template_pack=template_pack))

        return render_to_string(self.template, {
            'crispy_appended_text': self.appended_text,
            'crispy_prepended_text': self.prepended_text,
            'input_size': self.input_size,
            'active': getattr(self, 'active', False),
            'fields': fields,
            'field': bound_field,
            'css_id': attrs.get('id'),
            'css_class': attrs.get('class'),
            'field_class': field_class,
        }, context)


class Appended(PrependedAppended):
    def __init__(self, *args, **kwargs):
        kwargs.pop('appended_text', None)
        kwargs.pop('prepended_text', None)
        text = args[-1]
        fields = args[:-1]
        self.text = text
        super(Appended, self).__init__(*fields, appended_text=text, **kwargs)


class Prepended(PrependedAppended):
    def __init__(self, *args, **kwargs):
        kwargs.pop('appended_text', None)
        kwargs.pop('prepended_text', None)
        text = args[-1]
        fields = args[:-1]
        self.text = text
        super(Prepended, self).__init__(*fields, prepended_text=text, **kwargs)


class InputGroupButton(Div):
    css_class = 'input-group-btn'

    def __init__(self, field, *args, **kwargs):
        if isinstance(field, StrictButton):
            button = field
        else:
            button = StrictButton(field, **kwargs)
        super(InputGroupButton, self).__init__(*(args + (button,)), **kwargs)


class InputGroupAddon(Div):
    tag = 'span'
    css_class = 'input-group-addon'

    def __init__(self, field, **kwargs):
        super(InputGroupAddon, self).__init__(field, **kwargs)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        field = self.fields[0]
        if not hasattr(field, 'render'):
            bound_field = get_bound_field(context, form, field)
            if bound_field:
                field = RawField(field)
            else:
                field = HTML(field)
        fields = render_field(field, form, form_style, context, template_pack=template_pack)

        css_class = attrs.pop('class', self.css_class)

        context.update({
            'tag': self.tag,
            'form': form,
            'div': self,
            'fields': fields,
            'css_class': css_class,
            'flat_attrs': flatatt(attrs)
        })
        return render_to_string(self.template, context)


class InputGroup(Field):
    field_template = "%s/layout/raw_field.html" % TEMPLATE_PACK
    template = "%s/layout/prepended_appended.html" % TEMPLATE_PACK

    def __init__(self, *args, **kwargs):
        self.field = kwargs.pop('field', None)
        if 'active' in kwargs:
            self.active = kwargs.pop('active')

        self.input_size = None
        css_class = kwargs.get('css_class', '')
        if css_class.find('input-lg') != -1:
            self.input_size = 'input-lg'
        if css_class.find('input-sm') != -1:
            self.input_size = 'input-sm'

        super(InputGroup, self).__init__(*args, **kwargs)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        fields = []
        bound_field = None
        if self.field:
            bound_field = get_bound_field(context, form, self.field)
        for field in self.fields:
            if bound_field is None and isinstance(field, six.string_types):
                bound_field = get_bound_field(context, form, field)
            fields.append(render_field(field, form, form_style, context, template=self.field_template, template_pack=template_pack))

        return render_to_string(self.template, {
            'input_size': self.input_size,
            'active': getattr(self, 'active', False),
            'fields': fields,
            'field': bound_field,
            'flat_attrs': flatatt(attrs),
        }, context)


class Json(Template):
    def __init__(self, dictionary):
        self.dictionary = dictionary

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        dictionary = self._walk_render(self.dictionary, form, form_style, context, template_pack=TEMPLATE_PACK)
        return json.dumps(dictionary)


class FieldId(Renderizable):
    def __init__(self, field, suffix='', prefix='#'):
        self.field = field
        self.prefix = prefix
        self.suffix = suffix

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        field = get_bound_field(context, form, self.field)
        if not field:
            return ''
        return self.prefix + field.auto_id + self.suffix


class FieldVal(Renderizable):
    """
    Render a string using the field name at rendering time.

    This is particulary useful for lazy forms that will be loaded in containers
    (e.g. a div tag) whose id attribute contains the actual value of a given field.

    :param field: field name, which can include dots to specify fields within a
        form field in case of nested forms.
    :param suffix: suffix to prepend to the field value.
    :param prefix: prefix to append to the field value (defult '#').

    """
    def __init__(self, field, suffix='', prefix='', md5=False):
        self.field = field
        self.prefix = prefix
        self.suffix = suffix
        self.md5 = md5

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        value = resolve_value(context, self.field)
        value = force_text(value)
        if self.md5:
            value = hashlib.md5(value.encode('utf-8')).hexdigest()
        if not value:
            return ''
        return self.prefix + value + self.suffix


from crispy_forms.layout import Template as CrispyTemplate


class Template(CrispyTemplate):
    def __init__(self, template, *fields, **kwargs):
        self.fields = flatten_list(fields)
        self.template = template
        self.dictionary = kwargs.pop('dictionary', {})

    def replace_dots(self, name):
        return name.replace('.', '__')

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        fields = {}
        for field in self.fields:
            fields[self.replace_dots(field)] = resolve_value(context, field)
        dictionary = self._walk_render(self.dictionary, form, form_style, context, template_pack=TEMPLATE_PACK)
        dictionary.update(fields)
        return render_to_string(self.template, dictionary, context)


class Tour(Json):
    """
    Class that adds 'order' to the dictionary.
    """
    order = 0
    skip = set()

    def __init__(self, dictionary):
        super(Tour, self).__init__(dictionary)
        if 'order' in dictionary:
            self.__class__.skip.add(dictionary['order'])
        else:
            while self.__class__.order in self.__class__.skip:
                self.__class__.order += 1
            dictionary['order'] = self.__class__.order
            self.__class__.order += 1


class Anchor(Element):
    template = 'crispy_extra_fields/anchor.html'

    def __init__(self, url_encoder=None, text='', *args, **kwargs):
        self.text = text
        self.url_encoder = url_encoder
        self.field_classes = kwargs.pop('css_class', None)
        self.attrs = kwargs

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        if 'href' not in attrs:
            attrs['href'] = self.url_encoder and self.url_encoder(form) or 'javascript:;'

        context.update({
            'text': self.text,
            'field_classes': self.field_classes,
            'flat_attrs': flatatt(attrs),
        })
        return render_to_string(self.template, context)


from django.utils.encoding import smart_text


class Attribute(Renderizable):
    """
    Fetches an attribute at rendering time reacheable from the
    root form, the current form, or the visible context

    This is particulary useful for lazy forms and reuse of layouts from several
    forms acting like templates

    :param source: The initial object to be inspected to lookup name
        - current: The initial object is the current form being render_field
        - root: The initial object is the root of the form subtree
        - context: The initial object is fetched from the current context

    :param name: A non nested attribute name (defined at the given source)

    :param default: A default value on attribute resolution failure. The default
                    default value is the special value AttributeError, which
                    raises an AttributeError's exception on failure
    """
    def __init__(self, source, name, default=AttributeError):
        if source not in ('current', 'root', 'context'):
            raise Exception("Unknown source object %s" % source)
        self.source = source
        self.name = name
        self.default = default
        parts = self.name.split(".")
        self.head = parts[0]
        self.tail = parts[1:]

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        if self.source == 'context':
            obj = context.get(self.head, None)
        elif self.source == 'current':
            obj = getattr(form, self.head, None)
        else:
            obj = getattr(context['form'], self.head, None)

        if obj is None:
            obj = self.default
        else:
            for attr in self.tail:
                obj = getattr(obj, attr, None)
                if obj is None:
                    obj = self.default
                    break

        if AttributeError == obj:
            raise obj("source: %s, name: %s" % (self.source, self.name))

        if isinstance(obj, Renderizable):
            return obj.render(form, form_style, context, template_pack=TEMPLATE_PACK)
        else:
            return smart_text(obj)


def flush_row(row_items, col_count, current_justify_police):
    if len(row_items) == 0:
        row_items.append((HTML(''), 12))
    if current_justify_police == Block.JUSTIFY_LEFT:
        pass
    elif current_justify_police == Block.JUSTIFY_RIGHT:
        if col_count < 12:
            row_items = [(HTML(''), 12 - col_count)] + row_items
    elif current_justify_police == Block.JUSTIFY_FILL:
        row_items = [list(arg) for arg in row_items]
        while col_count < 12:
            for arg in row_items:
                arg[1] += 1
                col_count += 1
                if col_count == 12:
                    break
    elif current_justify_police == Block.JUSTIFY_CENTER:
        if col_count < 12:
            rem = 12 - col_count
            mid_left = int((rem + 0.5) / 2)
            mid_right = rem - mid_left
            if mid_right > 0:
                row_items.append((HTML(''), mid_right))
            row_items = [(HTML(''), mid_left)] + row_items

    div_items = []
    for arg in row_items:
        if len(arg) == 2:
            field, spancols = arg
            _kwargs = {}
        elif len(arg) == 3:
            field, spancols, _kwargs = arg
        _css_class = "col-xs-%s col-sm-%s col-md-%s" % (spancols, spancols, spancols)
        div_items.append(Div(field, css_class=_css_class, **_kwargs))
    return Div(*div_items, css_class='row')


def Block(*args, **kwargs):
    """ A medium level formatter. It produces a Div object per each item in
        the list of arguments

        Each argument is a integer command or (2 or 3)-tuples as follows:
            (LayoutObject, numcols) | (LayoutObject, numcols, div_kwargs)
             - Commands:
                Block.FLUSH: Flushes and justify the current row using the current justification policy

                Row's justification  policies, each command sets the justification policy until is changed
                all items are reviewed

                Block.JUSTIFY_LEFT <-- default
                Block.JUSTIFY_RIGHT
                Block.JUSTIFY_FILL
                Block.JUSTIFY_CENTER


            - LayoutObject: A LayoutObject
            - numcols: The number of columns to be assigned to the LayoutObject
            - div_kwargs: A dictionary with keyword arguments to be applied to the Div
                that envelops the LayoutObject numcols

        Notice that every 12 columns it will emit a Div(..., css_class='row')
        object enveloping the previous elements (with 12 columns accumulated, at most)

        Keyword arguments:
        - cols = Integer: The number of parent's columns being used by this block
        - row = Bool or Integer: Specifies the number of times the resulting Div will be
                 wrapped with Div(..., css_class='row'). Notice that this behavior is expected
                 to select a proper left-padding.
                 Boolean values are interpreted as 0 or 1 for False and True, respectively
        - extra arguments are directly sent to the Div's constructor

    """

    list_ = []
    row_items = []
    col_count = 0
    current_justify_police = Block.JUSTIFY_LEFT

    for arg in args:
        if isinstance(arg, types.IntType):
            if arg == Block.FLUSH:
                list_.append(flush_row(row_items, col_count, current_justify_police))
                row_items = []
                col_count = 0
            else:
                current_justify_police = arg
        elif isinstance(arg, types.TupleType):
            __cols = arg[1]
            # flush the last row
            if col_count + __cols > 12:
                list_.append(flush_row(row_items, col_count, current_justify_police))
                row_items = [arg]
                col_count = __cols
            else:
                col_count += __cols
                row_items.append(arg)
        else:
            # weird! but we don't know the width of arg
            list_.append(arg)

    if len(row_items) > 0:
        list_.append(flush_row(row_items, col_count, current_justify_police))

    _cols = kwargs.pop('cols', 12)
    _css_class = "col-xs-%s col-sm-%s col-md-%s col-lg-%s" % (_cols, _cols, _cols, _cols)
    # row = kwargs.pop('row', False)
    # if row:
    #     row = Div(*list_, css_class='row', **kwargs)
    #     #return Div(Div(row, css_class=_css_class), css_class='row')
    #     return Div(row, css_class=_css_class)
    # else:
    #     return Div(*list_, css_class=_css_class, **kwargs)
    row = int(kwargs.pop('row', 0))
    if row > 0:
        while row > 0:
            row -= 1
            list_ = [Div(*list_, css_class='row', **kwargs)]
        return Div(*list_, css_class=_css_class)
        #row = Div(*list_, css_class='row', **kwargs)
        #return Div(Div(row, css_class=_css_class), css_class='row')
    else:
        return Div(*list_, css_class=_css_class, **kwargs)

Block.FLUSH = 0
Block.JUSTIFY_LEFT = 1
Block.JUSTIFY_RIGHT = 2
Block.JUSTIFY_FILL = 3
Block.JUSTIFY_CENTER = 4


import collections


def flow_justify(row_items, col_id, col_count):
    while col_count < 12:
        for item in row_items:
            item.sizes[col_id] += 1
            col_count += 1
            if col_count == 12:
                break
    return


class FlowItem(object):
    def __init__(self, field, *sizes, **kwargs):
        if isinstance(field, types.StringTypes):
            field = Field(field)
        self.field = field
        self.identity = kwargs.pop('identity', False)
        self.kwargs = kwargs
        self._css_class = kwargs.pop('css_class', '')

        if self.identity:
            self.sizes = None
            self.fixedcols = True
        else:
            self.sizes = self.fix_sizes(sizes)
            self.fixedcols = kwargs.pop('fixedcols', False)

    @staticmethod
    def fix_sizes(sizes):
        sizes = list(sizes)
        if len(sizes) == 0:
            sizes.append(12)
        while len(sizes) < 4:
            sizes.append(sizes[-1])
        return sizes

    def css_class(self):
        return "col-xs-{0} col-sm-{1} col-md-{2} col-lg-{3}".format(*self.sizes) + " " + self._css_class

    @classmethod
    def static_css_class(cls, *sizes):
        return "col-xs-{0} col-sm-{1} col-md-{2} col-lg-{3}".format(*cls.fix_sizes(sizes))

    def renderizable(self):
        if self.identity:
            return self.field
        else:
            if isinstance(self.field, types.TupleType):
                return Div(*self.field, css_class=self.css_class(), **self.kwargs)
            else:
                return Div(self.field, css_class=self.css_class(), **self.kwargs)

    def __str__(self):
        if isinstance(self.field, Field):
            field = "Field(%s)" % repr(self.field.field)
        else:
            field = self.field
        args = [field]
        if len(self.sizes) > 0:
            args.extend(self.sizes)

        if self.identity:
            args.append("identity=True")

        if len(self.kwargs) > 0:
            args.append("**" + repr(self.kwargs))

        return "Flow.Item(%s)" % (", ".join(map(str, args)))


def Flow(*args, **kwargs):
    """ A medium level formatter of fields.

        It converts a stream of objects into a list of Div objects with a
        in a succinct way.

        Each object can be a single Flow.Item or Renderiable object or a nested structure (iterable) containing
        Flow.Items or Renderizable objects

        Parameters:

        :param posititional arguments: Field.Item objects. Each item is described as follows:
            Field.Item(Renderizable, xs[, sm[, md[, lg,]]] **kwargs)
            where xs,sm,dm,lg are the number of columns used by the field in the bootstrap3's display medium.
            If less than 4 are given then last value fixes the rest
        :param cols: A tuple describing the number of cols for the entire flow (xs,sm,md,lg). The behavior of Field.Item
            to handle the column's sizes is provided.
        :param jusfify: If justify is True then Flow expand items such that each row occupies 12 columns.

        Notice that it supports Renderizable objects, however, mixing with Flow.Items could
        produce they could produce unexpected behaviours.

    """

    list_ = []

    def collect_items(arglist):
        for arg in arglist:
            if isinstance(arg, FlowItem):
                list_.append(arg)
            elif isinstance(arg, types.StringTypes):
                list_.append(FlowItem(arg, 6))
            elif isinstance(arg, collections.Iterable):
                collect_items(arg)
            else:
                list_.append(FlowItem(arg, identity=True))

    collect_items(args)
    if kwargs.pop('justify', False):
        for colID in range(4):
            item_list = []
            acc = 0
            for itemID in range(len(list_)):
                item = list_[itemID]
                if item.identity:
                    continue
                if item.fixedcols:
                    acc += item.sizes[colID]
                elif acc + item.sizes[colID] > 12:
                    if len(item_list) == 0:
                        # only fixed size items
                        acc = 0
                    else:
                        flow_justify(item_list, colID, acc)
                        acc = item.sizes[colID]
                        item_list = [item]
                else:
                    acc += item.sizes[colID]
                    item_list.append(item)
            if len(item_list) > 0:
                flow_justify(item_list, colID, acc)
    list_ = [item.renderizable() for item in list_]
    _css_class = FlowItem.static_css_class(*kwargs.pop('cols', (12,)))
    row = int(kwargs.pop('row', 0))
    if row > 0:
        while row > 0:
            row -= 1
            list_ = [Div(*list_, css_class='row', **kwargs)]
        return Div(*list_, css_class=_css_class)
    else:
        return Div(*list_, css_class=_css_class, **kwargs)


Flow.Item = FlowItem
