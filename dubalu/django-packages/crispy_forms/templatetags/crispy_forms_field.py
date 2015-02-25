try:
    from itertools import izip
except ImportError:
    izip = zip

from django import forms
from django import template
from django.template import loader, Context
from django.conf import settings

from crispy_forms.utils import TEMPLATE_PACK
from crispy_forms.templatetags.crispy_forms_tags import do_crispy_form

register = template.Library()

class_converter = {
    "textinput": "textinput textInput",
    "fileinput": "fileinput fileUpload",
    "passwordinput": "textinput textInput",
}
class_converter.update(getattr(settings, 'CRISPY_CLASS_CONVERTERS', {}))


@register.filter
def is_form(field):
    return hasattr(field.field, 'form')


@register.filter
def is_formset(field):
    return hasattr(field.field, 'formset')


@register.filter
def is_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter
def is_password(field):
    return isinstance(field.field.widget, forms.PasswordInput)


@register.filter
def is_radioselect(field):
    return isinstance(field.field.widget, forms.RadioSelect)


@register.filter
def is_checkboxselectmultiple(field):
    return isinstance(field.field.widget, forms.CheckboxSelectMultiple)


@register.filter
def is_file(field):
    return isinstance(field.field.widget, forms.ClearableFileInput)


@register.filter
def classes(field):
    """
    Returns CSS classes of a field
    """
    return field.widget.attrs.get('class', None)


@register.filter
def css_class(field):
    """
    Returns widgets class name in lowercase
    """
    return field.field.widget.__class__.__name__.lower()


@register.simple_tag(takes_context=True, name="crispy_field")
def crispy_field(context, field, **attrs):
    html5_required = bool(context.get('html5_required'))

    class_name = field.field.widget.__class__.__name__.lower()
    class_name = class_converter.get(class_name, class_name)

    atributes = field.field.widget.attrs
    for attribute_name, attribute in atributes.items():
        if attribute_name in attrs:
            attrs[attribute_name] += " " + attribute
        else:
            attrs[attribute_name] = attribute

    css_class = attrs.get('class', '')
    if css_class:
        if css_class.find(class_name) == -1:
            css_class += " %s" % class_name
    else:
        css_class = class_name

    if (
        TEMPLATE_PACK == 'bootstrap3'
        and not is_checkbox(field)
        and not is_file(field)
    ):
        css_class += ' form-control'

    if field.field.required:
        css_class += ' required'

    if field.errors:
        css_class += ' has-error'

    attrs['class'] = css_class

    # HTML5 required attribute
    if html5_required and field.field.required and 'required' not in attrs:
        if class_name != 'radioselect':
            attrs['required'] = 'required'

    if field.field.show_hidden_initial:
        return field.as_widget(attrs=attrs) + field.as_hidden(only_initial=True)
    return field.as_widget(attrs=attrs)


@register.simple_tag(takes_context=True, name='crispy_form')
def crispy_form(context, form, helper=None, template_pack=TEMPLATE_PACK):
    return do_crispy_form(context, form, helper, template_pack, True)


@register.simple_tag()
def crispy_addon(field, append="", prepend=""):
    """
    Renders a form field using bootstrap's prepended or appended text::

        {% crispy_addon form.my_field prepend="$" append=".00" %}

    You can also just prepend or append like so

        {% crispy_addon form.my_field prepend="$" %}
        {% crispy_addon form.my_field append=".00" %}
    """
    if (field):
        context = Context({
            'field': field,
            'form_show_errors': True
        })

        template = loader.get_template('%s/layout/prepended_appended_text.html' % TEMPLATE_PACK)
        context['crispy_prepended_text'] = prepend
        context['crispy_appended_text'] = append

        if not prepend and not append:
            raise TypeError("Expected a prepend and/or append argument")

    return template.render(context)
