from __future__ import absolute_import, unicode_literals

import re
import inspect

from django.conf import settings
from django.core import urlresolvers
from django import template
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils import six

try:
    from dfw.utils.forms import FormFieldDict
except ImportError:
    FormFieldDict = None

from crispy_forms.compatibility import string_types
from crispy_forms.utils import render_field, flatatt, KeepContext, flatten_list, get_bound_field
from crispy_forms.exceptions import FormHelpersException

TEMPLATE_PACK = getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')


class Renderizable(object):
    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        raise NotImplementedError

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        with KeepContext(context):
            if FormFieldDict and hasattr(form, 'fields'):
                if '__form_%d' % id(form) not in context:
                    context.update(form.initial)
                    context.update(FormFieldDict(form))
            if 'template_pack' in inspect.getargspec(self._render)[0]:
                return self._render(form, form_style, context, template_pack=template_pack)
            else:
                return self._render(form, form_style, context)


class LayoutObject(Renderizable):
    def __getitem__(self, slice):
        return self.fields[slice]

    def __setitem__(self, slice, value):
        self.fields[slice] = value

    def __delitem__(self, slice):
        del self.fields[slice]

    def __len__(self):
        return len(self.fields)

    def __getattr__(self, name):
        """
        This allows us to access self.fields list methods like append or insert, without
        having to declaee them one by one
        """
        # Check necessary for unpickling, see #107
        if 'fields' in self.__dict__ and hasattr(self.fields, name):
            return getattr(self.fields, name)
        else:
            return object.__getattribute__(self, name)

    def get_field_names(self, index=None):
        """
        Returns a list of lists, those lists are named pointers. First parameter
        is the location of the field, second one the name of the field. Example::

            [
               [[0,1,2], 'field_name1'],
               [[0,3], 'field_name2']
            ]
        """
        return self.get_layout_objects(string_types, greedy=True)

    def get_layout_objects(self, *LayoutClasses, **kwargs):
        """
        Returns a list of lists pointing to layout objects of any type matching
        `LayoutClasses`::

            [
               [[0,1,2], 'div'],
               [[0,3], 'field_name']
            ]

        :param max_level: An integer that indicates max level depth to reach when
        traversing a layout.
        :param greedy: Boolean that indicates whether to be greedy. If set, max_level
        is skipped.
        """
        index = kwargs.pop('index', None)
        max_level = kwargs.pop('max_level', 0)
        greedy = kwargs.pop('greedy', False)

        pointers = []

        if index is not None and not isinstance(index, list):
            index = [index]
        elif index is None:
            index = []

        for i, layout_object in enumerate(self.fields):
            if isinstance(layout_object, LayoutClasses):
                if len(LayoutClasses) == 1 and LayoutClasses[0] == string_types:
                    pointers.append([index + [i], layout_object])
                else:
                    pointers.append([index + [i], layout_object.__class__.__name__.lower()])

            # If it's a layout object and we haven't reached the max depth limit or greedy
            # we recursive call
            if hasattr(layout_object, 'get_field_names') and (len(index) < max_level or greedy) and hasattr(layout_object, 'fields'):
                new_kwargs = {'index': index + [i], 'max_level': max_level, 'greedy': greedy}
                pointers = pointers + layout_object.get_layout_objects(*LayoutClasses, **new_kwargs)

        return pointers


class Element(LayoutObject):
    css_class = None
    css_id = None

    def get_attrs(self, form, form_style, context, template_pack=TEMPLATE_PACK, _attrs=None):
        # We use kwargs as HTML attributes, turning data_id='test' into data-id='test'
        if _attrs is None:
            _attrs = self.attrs
        attrs = {}
        for k, v in _attrs.items():
            if isinstance(k, Renderizable):
                k = k.render(form, form_style, context, template_pack=template_pack)
            k = k.replace('_', '-')
            if isinstance(v, Renderizable):
                v = v.render(form, form_style, context, template_pack=template_pack)
            v = escape(v)
            attrs[k] = v

        if self.css_id:
            attrs['id'] = self.css_id

        if 'css-id' in attrs:
            attrs['id'] = attrs.pop('css-id')

        if self.css_class:
            if 'class' in attrs:
                attrs['class'] += " %s" % self.css_class
            else:
                attrs['class'] = self.css_class

        if 'css-class' in attrs:
            if 'class' in attrs:
                attrs['class'] += " %s" % attrs.pop('css-class')
            else:
                attrs['class'] = attrs.pop('css-class')

        return attrs


class BaseLayout(object):
    inputs = None
    _form_method = None
    _form_action = None
    _form_style = None
    form = None
    form_id = None
    form_class = None
    form_tag = None
    form_error_title = None
    formset_error_title = None
    form_show_errors = None
    render_unmentioned_fields = None
    render_hidden_fields = None
    render_required_fields = None
    _help_text_inline = False
    _error_text_inline = True
    html5_required = None
    form_show_labels = None
    template = None
    field_template = None
    disable_csrf = None
    field_class = None
    label_class = None
    label_offset = None

    def add_input(self, input_object):
        if self.inputs is None:
            self.inputs = []
        self.inputs.append(input_object)

    def get_form_method(self):
        return self._form_method

    def set_form_method(self, method):
        if method.lower() not in ('get', 'post'):
            raise FormHelpersException('Only GET and POST are valid in the \
                    form_method helper attribute')
        self._form_method = method.lower()

    # we set properties the old way because we want to support pre-2.6 python
    form_method = property(get_form_method, set_form_method)

    def get_form_action(self):
        try:
            return urlresolvers.reverse(self._form_action)
        except urlresolvers.NoReverseMatch:
            return self._form_action

    def set_form_action(self, action):
        self._form_action = action

    # we set properties the old way because we want to support pre-2.6 python
    form_action = property(get_form_action, set_form_action)

    def get_form_style(self):
        if self._form_style == 'default':
            return ''
        if self._form_style == 'inline':
            return 'inlineLabels'

    def set_form_style(self, style):
        if style.lower() not in ('default', 'inline'):
            raise FormHelpersException('Only default and inline are valid in the \
                    form_style helper attribute')
        self._form_style = style.lower()

    # we set properties the old way because we want to support pre-2.6 python
    form_style = property(get_form_style, set_form_style)

    def get_help_text_inline(self):
        return self._help_text_inline

    def set_help_text_inline(self, flag):
        self._help_text_inline = flag
        self._error_text_inline = not flag

    help_text_inline = property(get_help_text_inline, set_help_text_inline)

    def get_error_text_inline(self):
        return self._error_text_inline

    def set_error_text_inline(self, flag):
        self._error_text_inline = flag
        self._help_text_inline = not flag

    # we set properties the old way because we want to support pre-2.6 python
    error_text_inline = property(get_error_text_inline, set_error_text_inline)


class Layout(LayoutObject, BaseLayout):
    """
    Form Layout. It is conformed by Layout objects: `Fieldset`, `Row`, `Column`, `MultiField`,
    `HTML`, `ButtonHolder`, `Button`, `Hidden`, `Reset`, `Submit` and fields. Form fields
    have to be strings.
    Layout objects `Fieldset`, `Row`, `Column`, `MultiField` and `ButtonHolder` can hold other
    Layout objects within. Though `ButtonHolder` should only hold `HTML` and BaseInput
    inherited classes: `Button`, `Hidden`, `Reset` and `Submit`.

    You need to add your `Layout` to the `FormHelper` using its method `add_layout`.

    Example::

        layout = Layout(
            Fieldset('Company data',
                'is_company'
            ),
            Fieldset(_('Contact details'),
                'email',
                Row('password1', 'password2'),
                'first_name',
                'last_name',
                HTML('<img src="/media/somepicture.jpg"/>'),
                'company'
            ),
            ButtonHolder(
                Submit('Save', 'Save', css_class='button white'),
            ),
        )

        helper.add_layout(layout)
    """
    # Some defaults for layouts:
    _form_method = 'post'
    _form_action = ''
    _form_style = 'default'
    form_id = ''
    form_class = ''
    form_tag = True
    form_show_errors = True
    render_unmentioned_fields = False
    render_hidden_fields = False
    render_required_fields = False
    _help_text_inline = False
    _error_text_inline = True
    html5_required = False
    form_show_labels = True
    disable_csrf = False
    field_class = ''
    label_class = ''
    label_offset = ''

    def __init__(self, *fields, **kwargs):
        self.fields = flatten_list(fields)
        self.attrs = kwargs.pop('attrs', {})
        self.inputs = kwargs.pop('inputs', [])
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_attributes(self, helper=None, template_pack=TEMPLATE_PACK):
        """
        Used by crispy_forms_tags to get helper and layout attributes

        """
        def a(attr):
            val = None
            if helper is not None:
                val = getattr(helper, attr)
            if val is None:
                val = getattr(self, attr)
            return val

        items = {}

        items['form_method'] = a('form_method').strip()
        items['form_tag'] = a('form_tag')
        items['form_style'] = a('form_style').strip()
        items['form_show_errors'] = a('form_show_errors')
        items['help_text_inline'] = a('help_text_inline')
        items['error_text_inline'] = a('error_text_inline')
        items['html5_required'] = a('html5_required')
        items['form_show_labels'] = a('form_show_labels')
        items['disable_csrf'] = a('disable_csrf')

        # Bootstrap label and field classes (label_offset is automatically calculated from label_class)
        items['label_class'] = a('label_class')
        items['field_class'] = a('field_class')
        label_offset_match = re.findall('col-(xs|sm|md|lg)-(\d+)', items['label_class'])
        if label_offset_match:
            label_offset = []
            for m in label_offset_match:
                label_offset.append('col-%s-offset-%s' % m)
            items['label_offset'] = ' '.join(label_offset)

        items['attrs'] = {}
        if self.attrs:
            items['attrs'] = self.attrs.copy()
        if a('form_action'):
            items['attrs']['action'] = a('form_action').strip()
        if a('form_id'):
            items['attrs']['id'] = a('form_id').strip()
        if a('form_class'):
            # uni_form TEMPLATE PACK has a uniForm class by default
            if template_pack == 'uni_form':
                items['attrs']['class'] = "uniForm %s" % a('form_class').strip()
            else:
                items['attrs']['class'] = a('form_class').strip()
        else:
            if template_pack == 'uni_form':
                items['attrs']['class'] = self.attrs.get('class', '') + " uniForm"

        items['flat_attrs'] = flatatt(items['attrs'])

        if a('inputs'):
            items['inputs'] = a('inputs')
        if a('form_error_title'):
            items['form_error_title'] = a('form_error_title').strip()
        if a('formset_error_title'):
            items['formset_error_title'] = a('formset_error_title').strip()

        for attribute_name, value in self.__dict__.items():
            if attribute_name not in items and attribute_name not in ['layout', 'inputs'] and not attribute_name.startswith('_'):
                items[attribute_name] = value

        return items

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        html = ""
        for field in self.fields:
            html += render_field(
                field,
                form,
                form_style,
                context,
                template_pack=template_pack
            )
        return html

    def render_layout(self, form, context, template_pack=TEMPLATE_PACK):
        """
        Returns safe html of the rendering of the layout
        """
        form.rendered_fields = set()
        form.crispy_field_template = self.field_template

        # This renders the specifed Layout strictly
        html = self.render(
            form,
            self.form_style,
            context,
            template_pack=template_pack
        )

        # Rendering some extra fields if specified
        if self.render_unmentioned_fields or self.render_hidden_fields or self.render_required_fields:
            fields = set(form.fields.keys())
            left_fields_to_render = fields - form.rendered_fields
            for field in left_fields_to_render:
                if (
                    self.render_unmentioned_fields or
                    self.render_hidden_fields and form.fields[field].widget.is_hidden or
                    self.render_required_fields and form.fields[field].widget.is_required
                ):
                    html += render_field(
                        field,
                        form,
                        self.form_style,
                        context,
                        template_pack=template_pack
                    )

        # If the user has Meta.fields defined, not included in the layout,
        # we suppose they need to be rendered
        if hasattr(form, 'Meta'):
            if hasattr(form.Meta, 'fields'):
                current_fields = set(getattr(form, 'fields', []))
                meta_fields = set(getattr(form.Meta, 'fields'))

                fields_to_render = current_fields & meta_fields
                left_fields_to_render = fields_to_render - form.rendered_fields

                for field in left_fields_to_render:
                    html += render_field(field, form, self.form_style, context)

        return mark_safe(html)


class ButtonHolder(Element):
    """
    Layout object. It wraps fields in a <div class="buttonHolder">

    This is where you should put Layout objects that render to form buttons like Submit.
    It should only hold `HTML` and `BaseInput` inherited objects.

    Example::

        ButtonHolder(
            HTML(<span style="display: hidden;">Information Saved</span>),
            Submit('Save', 'Save')
        )
    """
    template = "uni_form/layout/buttonholder.html"

    def __init__(self, *fields, **kwargs):
        self.fields = flatten_list(fields)
        self.css_class = kwargs.get('css_class', None)
        self.css_id = kwargs.get('css_id', None)
        self.template = kwargs.get('template', self.template)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        html = ''
        for field in self.fields:
            html += render_field(field, form, form_style,
                                 context, template_pack=template_pack)

        context.update({'buttonholder': self, 'fields_output': html})
        return render_to_string(self.template, context)


class BaseInput(Element):
    """
    A base class to reduce the amount of code in the Input classes.
    """
    template = "%s/layout/baseinput.html" % TEMPLATE_PACK

    def __init__(self, name, value, **kwargs):
        self.name = name
        self.value = value
        self.value_template = template.get_template_from_string(self.value) if isinstance(self.value, six.string_types) else None
        self.id = kwargs.pop('css_id', '')
        self.attrs = {}

        if 'css_class' in kwargs:
            self.field_classes += ' %s' % kwargs.pop('css_class')

        self.template = kwargs.pop('template', self.template)
        self.attrs = kwargs

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        """
        Renders an `<input />` if container is used as a Layout object.
        Input button value can be a variable in context.
        """
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        value = self.value_template.render(context) if self.value_template else self.value
        if isinstance(value, Renderizable):
            value = value.render(form, form_style, context)

        context.update({
            'form': form,
            'input': self,
            'value': value,
            'flat_attrs': flatatt(attrs),
        })
        return render_to_string(self.template, context)


class Submit(BaseInput):
    """
    Used to create a Submit button descriptor for the {% crispy %} template tag::

        submit = Submit('Search the Site', 'search this site')

    .. note:: The first argument is also slugified and turned into the id for the submit button.
    """
    input_type = 'submit'
    field_classes = 'submit submitButton' if TEMPLATE_PACK == 'uni_form' else 'btn btn-primary'


class Button(BaseInput):
    """
    Used to create a Submit input descriptor for the {% crispy %} template tag::

        button = Button('Button 1', 'Press Me!')

    .. note:: The first argument is also slugified and turned into the id for the button.
    """
    input_type = 'button'
    field_classes = 'button' if TEMPLATE_PACK == 'uni_form' else 'btn'


class Hidden(BaseInput):
    """
    Used to create a Hidden input descriptor for the {% crispy %} template tag.
    """
    input_type = 'hidden'
    field_classes = 'hidden'


class Reset(BaseInput):
    """
    Used to create a Reset button input descriptor for the {% crispy %} template tag::

        reset = Reset('Reset This Form', 'Revert Me!')

    .. note:: The first argument is also slugified and turned into the id for the reset.
    """
    input_type = 'reset'
    field_classes = 'reset resetButton' if TEMPLATE_PACK == 'uni_form' else 'btn btn-inverse'


class Fieldset(Element):
    """
    Layout object. It wraps fields in a <fieldset>

    Example::

        Fieldset("Text for the legend",
            'form_field_1',
            'form_field_2'
        )

    The first parameter is the text for the fieldset legend. This text is context aware,
    so you can do things like::

        Fieldset("Data for {{ user.username }}",
            'form_field_1',
            'form_field_2'
        )
    """
    template = "uni_form/layout/fieldset.html"

    def __init__(self, legend, *fields, **kwargs):
        self.fields = flatten_list(fields)
        self.legend = legend
        self.legend_template = template.get_template_from_string(self.legend) if isinstance(self.legend, six.string_types) else None

        # Overrides class variable with an instance level variable
        self.template = kwargs.pop('template', self.template)
        self.legend_class = kwargs.pop('legend_class', None)

        self.attrs = kwargs

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        fields = ''
        for field in self.fields:
            fields += render_field(field, form, form_style, context,
                                   template_pack=template_pack)

        legend = self.legend_template.render(context) if self.legend_template else self.legend
        if isinstance(legend, Renderizable):
            legend = legend.render(form, form_style, context)

        context.update({
            'form': form,
            'fieldset': self,
            'legend': legend,
            'fields': fields,
            'form_style': form_style,
            'flat_attrs': flatatt(attrs),
        })
        return render_to_string(self.template, context)


class MultiField(Element):
    """ MultiField container. Renders to a MultiField <div> """
    template = "uni_form/layout/multifield.html"
    field_template = "uni_form/multifield.html"

    def __init__(self, label, *fields, **kwargs):
        self.fields = flatten_list(fields)
        self.show_labels = kwargs.pop('show_labels', None)
        self.label_html = label
        self.label_class = kwargs.pop('label_class', 'blockLabel')
        self.css_class = kwargs.pop('css_class', 'ctrlHolder')
        self.css_id = kwargs.pop('css_id', None)
        self.template = kwargs.pop('template', self.template)
        self.field_template = kwargs.pop('field_template', self.field_template)
        self.flat_attrs = flatatt(kwargs)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        # If a field within MultiField contains errors
        if context['form_show_errors']:
            for field in map(lambda pointer: pointer[1], self.get_field_names()):
                if field in form.errors:
                    self.css_class += " error"

        fields_output = ''
        for field in self.fields:
            fields_output += render_field(
                field, form, form_style, context,
                self.field_template, self.label_class, layout_object=self,
                template_pack=template_pack,
                show_labels=self.show_labels
            )

        context.update({'multifield': self, 'fields_output': fields_output})
        return render_to_string(self.template, context)


class Div(Element):
    """
    Layout object. It wraps fields in a <div>

    You can set `css_id` for a DOM id and `css_class` for a DOM class. Example::

        Div('form_field_1', 'form_field_2', css_id='div-example', css_class='divs')
    """
    tag = 'div'
    template = "uni_form/layout/div.html"

    def __init__(self, *fields, **kwargs):
        self.fields = flatten_list(fields)

        self.template = kwargs.pop('template', self.template)
        self.attrs = kwargs

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        fields = ''
        for field in self.fields:
            fields += render_field(field, form, form_style, context, template_pack=template_pack)

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


class Span(Div):
    tag = 'span'


class Row(Div):
    """
    Layout object. It wraps fields in a div whose default class is "formRow". Example::

        Row('form_field_1', 'form_field_2', 'form_field_3')
    """
    css_class = 'formRow' if TEMPLATE_PACK == 'uni_form' else 'row'


class Column(Div):
    """
    Layout object. It wraps fields in a div whose default class is "formColumn". Example::

        Column('form_field_1', 'form_field_2')
    """
    css_class = 'formColumn'


class Template(Renderizable):
    """
    Layout object. It can references a template and it has access to the whole
    context of the page where the form is being rendered. Optionally receives
    ``extra_context``.

    Examples::

        Template('my-template.html')
        Template('my-other-template.html', {'extra': "Extra!"})
    """

    def __init__(self, template, dictionary=None):
        self.template = template
        self.dictionary = dictionary or {}

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        dictionary = self._walk_render(self.dictionary, form, form_style, context, template_pack=TEMPLATE_PACK)
        return render_to_string(self.template, dictionary, context)

    def _walk_render(self, item, form, form_style, context, template_pack=TEMPLATE_PACK):
        if isinstance(item, (tuple, list)):
            return [self._walk_render(i, form, form_style, context, template_pack) for i in item]
        elif isinstance(item, dict):
            return dict((
                self._walk_render(k, form, form_style, context, template_pack),
                self._walk_render(v, form, form_style, context, template_pack)
            ) for k, v in item.items())
        elif isinstance(item, Renderizable):
            return item.render(form, form_style, context, template_pack=template_pack)
        elif isinstance(item, (int, long, float, bool)):
            return item
        else:
            return force_text(item)


class HTML(Template):
    """
    Layout object. It can contain pure HTML and it has access to the whole
    context of the page where the form is being rendered.

    Examples::

        HTML("{% if saved %}Data saved{% endif %}")
        HTML('<input type="hidden" name="{{ step_field }}" value="{{ step0 }}" />')
    """

    def __init__(self, html, dictionary=None):
        self.html = html
        self.html_template = template.get_template_from_string(self.html) if isinstance(self.html, six.string_types) else None
        self.dictionary = dictionary or {}

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        dictionary = self._walk_render(self.dictionary, form, form_style, context, template_pack=TEMPLATE_PACK)
        context.update(dictionary)
        html = self.html_template.render(context) if self.html_template else self.html
        if isinstance(html, Renderizable):
            html = html.render(form, form_style, context)
        return html


class Field(Element):
    """
    Layout object, It contains one field name, and you can add attributes to it easily.
    For setting class attributes, you need to use `css_class`, as `class` is a Python keyword.

    Example::

        Field('field_name', style="color: #333;", css_class="whatever", id="field_name")
    """
    template = "%s/field.html" % TEMPLATE_PACK

    def __init__(self, *args, **kwargs):
        self.fields = flatten_list(args)
        self.show_labels = kwargs.pop('show_labels', None)
        self.helper = kwargs.pop('helper', None)
        self.field = kwargs.pop('field', None)

        if self.field is None:
            for field in self.fields:
                if isinstance(field, six.string_types):
                    self.field = field
                    break

        self.wrapper_class = kwargs.pop('wrapper_class', None)
        self.template = kwargs.pop('template', self.template)

        self.attrs = kwargs

    def get_attrs(self, form, form_style, context, template_pack=TEMPLATE_PACK, _attrs=None):
        attrs = super(Field, self).get_attrs(form, form_style, context, template_pack=template_pack, _attrs=_attrs)

        if self.field in form.fields:
            actual_field = form.fields[self.field]
        elif self.field:
            actual_field = get_bound_field(context, form, self.field)
        else:
            actual_field = None

        if actual_field:
            if 'title' not in attrs:
                title = actual_field.help_text
                if title:
                    attrs['title'] = title
            if 'placeholder' not in attrs:
                placeholder = actual_field.label
                if placeholder:
                    attrs['placeholder'] = placeholder

        if 'title' in attrs:
            attrs['data-tooltip'] = 'tooltip'

        return attrs

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        if hasattr(self, 'wrapper_class'):
            context['wrapper_class'] = self.wrapper_class

        if self.helper:
            context['helper'] = self.helper

        html = ''
        for field in self.fields:
            html += render_field(field, form, form_style, context, template=self.template, attrs=attrs, template_pack=template_pack, show_labels=self.show_labels)
        return html


class MultiWidgetField(Field):
    """
    Layout object. For fields with :class:`~django.forms.MultiWidget` as `widget`, you can pass
    additional attributes to each widget.

    Example::

        MultiWidgetField(
            'multiwidget_field_name',
            attrs=(
                {'style': 'width: 30px;'},
                {'class': 'second_widget_class'}
            ),
        )

    .. note:: To override widget's css class use ``class`` not ``css_class``.
    """
    def get_attrs(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        return tuple(super(Field, self).get_attrs(form, form_style, context, template_pack=template_pack, _attrs=_attrs) for _attrs in self.attrs)

    def __init__(self, *args, **kwargs):
        self.fields = flatten_list(args)
        self.attrs = kwargs.pop('attrs', ())
        self.template = kwargs.pop('template', self.template)
