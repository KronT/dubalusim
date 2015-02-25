from __future__ import absolute_import, unicode_literals

import warnings
from random import randint

from django import template
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils.encoding import force_text
from django.utils import six

from .layout import Renderizable, Element, Field, Div
from .utils import render_field, flatatt, TEMPLATE_PACK, flatten_list


def make_id(value):
    return slugify(force_text(value)).replace('.', '-')


class PrependedAppendedText(Field):
    template = "%s/layout/prepended_appended_text.html" % TEMPLATE_PACK

    def __init__(self, field, prepended_text=None, appended_text=None, *args, **kwargs):
        self.appended_text = appended_text
        self.prepended_text = prepended_text
        self.active = kwargs.pop('active', None)
        self.input_size = None
        css_class = kwargs.get('css_class', '')
        if css_class.find('input-lg') != -1:
            self.input_size = 'input-lg'
        if css_class.find('input-sm') != -1:
            self.input_size = 'input-sm'

        super(PrependedAppendedText, self).__init__(field, *args, **kwargs)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=template_pack)

        context.update({
            'crispy_appended_text': self.appended_text,
            'crispy_prepended_text': self.prepended_text,
            'input_size': self.input_size,
            'active': self.active,
        })
        return render_field(self.field, form, form_style, context, template=self.template, attrs=attrs, template_pack=template_pack, show_labels=self.show_labels)


class AppendedPrependedText(PrependedAppendedText):
    def __init__(self, *args, **kwargs):
        warnings.warn("AppendedPrependedText has been renamed to PrependedAppendedText, \
            it will be removed in 1.3.0", PendingDeprecationWarning)
        super(AppendedPrependedText, self).__init__(*args, **kwargs)


class AppendedText(PrependedAppendedText):
    def __init__(self, field, text, *args, **kwargs):
        kwargs.pop('appended_text', None)
        kwargs.pop('prepended_text', None)
        self.text = text
        super(AppendedText, self).__init__(field, appended_text=text, **kwargs)


class PrependedText(PrependedAppendedText):
    def __init__(self, field, text, *args, **kwargs):
        kwargs.pop('appended_text', None)
        kwargs.pop('prepended_text', None)
        self.text = text
        super(PrependedText, self).__init__(field, prepended_text=text, **kwargs)


class FormActions(Element):
    """
    Bootstrap layout object. It wraps fields in a <div class="form-actions">

    Example::

        FormActions(
            HTML(<span style="display: hidden;">Information Saved</span>),
            Submit('Save', 'Save', css_class='btn-primary')
        )
    """
    template = "%s/layout/formactions.html" % TEMPLATE_PACK

    def __init__(self, *fields, **kwargs):
        self.fields = flatten_list(fields)
        self.template = kwargs.pop('template', self.template)
        self.attrs = kwargs

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        attrs = self.get_attrs(form, form_style, context, template_pack=TEMPLATE_PACK)

        html = ''
        for field in self.fields:
            html += render_field(field, form, form_style, context, template_pack=template_pack)

        context.update({
            'formactions': self,
            'fields_output': html,
            'flat_attrs': flatatt(attrs),

        })
        return render_to_string(self.template, context)


class InlineCheckboxes(Field):
    """
    Layout object for rendering checkboxes inline::

        InlineCheckboxes('field_name')
    """
    template = "%s/layout/checkboxselectmultiple_inline.html" % TEMPLATE_PACK

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        context.update({'inline_class': 'inline'})
        return super(InlineCheckboxes, self)._render(form, form_style, context)


class InlineRadios(Field):
    """
    Layout object for rendering radiobuttons inline::

        InlineRadios('field_name')
    """
    template = "%s/layout/radioselect_inline.html" % TEMPLATE_PACK

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        context.update({'inline_class': 'inline'})
        return super(InlineRadios, self)._render(form, form_style, context)


class FieldWithButtons(Div):
    template = '%s/layout/field_with_buttons.html' % TEMPLATE_PACK

    def __init__(self, *fields, **kwargs):
        self.show_labels = kwargs.pop('show_labels', None)
        super(FieldWithButtons, self).__init__(*fields, **kwargs)

    def _render(self, form, form_style, context):
        # We first render the buttons
        buttons = ''
        for field in self.fields[1:]:
            buttons += render_field(
                field, form, form_style, context,
                '%s/layout/field.html' % TEMPLATE_PACK, layout_object=self, show_labels=self.show_labels
            )

        context.update({'div': self, 'buttons': buttons})

        if isinstance(self.fields[0], Field):
            # FieldWithButtons(Field('field_name'), StrictButton("go"))
            # We render the field passing its name and attributes
            return render_field(
                self.fields[0][0], form, form_style, context,
                self.template, attrs=self.fields[0].attrs
            )
        else:
            return render_field(self.fields[0], form, form_style, context, self.template)


class StrictButton(Element):
    """
    Layout oject for rendering an HTML button::

        Button("button content", css_class="extra")
    """
    template = '%s/layout/button.html' % TEMPLATE_PACK
    css_class = 'btn'

    def __init__(self, content, **kwargs):
        self.content = content
        self.content_template = template.get_template_from_string(self.content) if isinstance(self.content, six.string_types) else None
        self.template = kwargs.pop('template', self.template)

        kwargs.setdefault('type', 'button')

        self.attrs = kwargs

    def _render(self, form, form_style, context):
        attrs = self.get_attrs(form, form_style, context, template_pack=TEMPLATE_PACK)
        content = self.content_template.render(context) if self.content_template else self.content
        if isinstance(content, Renderizable):
            content = content.render(form, form_style, context)
        context.update({
            'button': self,
            'content': content,
            'flat_attrs': flatatt(attrs),
        })
        return render_to_string(self.template, context)


class Container(Div):
    """
    Base class used for `Tab` and `AccordionGroup`, represents a basic container concept
    """
    css_class = ""

    def __init__(self, name, *fields, **kwargs):
        super(Container, self).__init__(*fields, **kwargs)
        self.template = kwargs.pop('template', self.template)
        self.name = name
        self.active = kwargs.pop('active', None)
        if not self.css_id:
            self.css_id = make_id(self.name)

    def __contains__(self, field_name):
        """
        check if field_name is contained within tab.
        """
        return field_name in map(lambda pointer: pointer[1], self.get_field_names())

    def _render(self, form, form_style, context):
        if self.active is not None:
            context['active'] = self.active
        return super(Container, self)._render(form, form_style, context)


class ContainerHolder(Div):
    """
    Base class used for `TabHolder` and `Accordion`, groups containers
    """
    def first_container_with_errors(self, errors):
        """
        Returns the first container with errors, otherwise returns the first one
        """
        for tab in self.fields:
            errors_here = any(error in tab for error in errors)
            if errors_here:
                return tab

        return self.fields[0]


class Tab(Container):
    """
    Tab object. It wraps fields in a div whose default class is "tab-pane" and
    takes a name as first argument. Example::

        Tab('tab_name', 'form_field_1', 'form_field_2', 'form_field_3')
    """
    css_class = 'tab-pane'
    link_template = '%s/layout/tab-link.html' % TEMPLATE_PACK

    def render_link(self, context):
        """
        Render the link for the tab-pane. It must be called after render so css_class is updated
        with active if needed.
        """
        context.update({'link': self})
        return render_to_string(self.link_template, context)

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        """
        inject the form prefix. This is aimed to support nestedforms.
        """
        if form.prefix:
            self.css_id = '-'.join((form.prefix, make_id(self.name), 'tab'))  # this should be handled in a local variable to make it thread-safe
        return super(Tab, self)._render(form, form_style, context)


class TabHolder(ContainerHolder):
    """
    TabHolder object. It wraps Tab objects in a container. Requires bootstrap-tab.js::

        TabHolder(
            Tab('form_field_1', 'form_field_2'),
            Tab('form_field_3')
        )
    """
    template = '%s/layout/tab.html' % TEMPLATE_PACK

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        links, content = '', ''
        # The first tab with errors will be active
        active = self.first_container_with_errors(form.errors.keys())

        for tab in self.fields:
            context['active'] = tab == active
            content += render_field(
                tab, form, form_style, context, template_pack=template_pack
            )
            links += tab.render_link(context)

        context.update({'tabs': self, 'links': links, 'content': content})
        return render_to_string(self.template, context)


class AccordionGroup(Container):
    """
    Accordion Group (pane) object. It wraps given fields inside an accordion
    tab. It takes accordion tab name as first argument::

        AccordionGroup("group name", "form_field_1", "form_field_2")
    """
    template = "%s/accordion-group.html" % TEMPLATE_PACK


class Accordion(ContainerHolder):
    """
    Accordion menu object. It wraps `AccordionGroup` objects in a container::

        Accordion(
            AccordionGroup("group name", "form_field_1", "form_field_2"),
            AccordionGroup("another group name", "form_field")
        )
    """
    template = "%s/accordion.html" % TEMPLATE_PACK

    def _render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        content = ''

        # accordion group needs the parent div id to set `data-parent` (I don't
        # know why). This needs to be a unique id
        css_id = self.css_id or '-'.join(['accordion', force_text(randint(1000, 9999))])

        # first group with errors or first groupt will be visible, others will be collapsed
        active = self.first_container_with_errors(form.errors.keys())

        for group in self.fields:
            context['data_parent'] = css_id
            context['active'] = group == active
            content += render_field(
                group, form, form_style, context, template_pack=template_pack
            )

        context.update({'accordion': self, 'content': content, 'css_id': css_id})
        return render_to_string(self.template, context)


class Alert(Div):
    """
    `Alert` generates markup in the form of an alert dialog

        Alert(content='<strong>Warning!</strong> Best check yo self, you're not looking too good.')
    """
    template = "bootstrap/layout/alert.html"
    css_class = "alert"

    def __init__(self, content, dismiss=True, block=False, **kwargs):
        fields = []
        if block:
            self.css_class += ' alert-block'
        super(Alert, self).__init__(self, *fields, **kwargs)
        self.template = kwargs.pop('template', self.template)
        self.content = content
        self.dismiss = dismiss

    def _render(self, form, form_style, context):
        context.update({'alert': self, 'content': self.content, 'dismiss': self.dismiss})
        return render_to_string(self.template, context)


class UneditableField(Field):
    """
    Layout object for rendering fields as uneditable in bootstrap

    Example::

        UneditableField('field_name', css_class="input-xlarge")
    """
    template = "%s/layout/uneditable_input.html" % TEMPLATE_PACK

    def __init__(self, field, *args, **kwargs):
        self.attrs = {'class': 'uneditable-input'}
        super(UneditableField, self).__init__(field, *args, **kwargs)


class InlineField(Field):
    template = "%s/layout/inline_field.html" % TEMPLATE_PACK
