# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.forms.formsets import BaseFormSet

from crispy_forms.compatibility import string_types
from crispy_forms.layout import Layout, Submit, BaseLayout
from crispy_forms.layout_slice import LayoutSlice
from crispy_forms.exceptions import FormHelpersException


class DynamicLayoutHandler(object):
    def _check_layout(self):
        if self.layout is None:
            raise FormHelpersException("You need to set a layout in your FormHelper")

    def _check_layout_and_form(self):
        self._check_layout()
        if self.form is None:
            raise FormHelpersException("You need to pass a form instance to your FormHelper")

    def all(self):
        """
        Returns all layout objects of first level of depth
        """
        self._check_layout()
        return LayoutSlice(self.layout, slice(0, len(self.layout.fields), 1))

    def filter(self, *LayoutClasses, **kwargs):
        """
        Returns a LayoutSlice pointing to layout objects of type `LayoutClass`
        """
        self._check_layout()
        max_level = kwargs.pop('max_level', 0)
        greedy = kwargs.pop('greedy', False)
        filtered_layout_objects = self.layout.get_layout_objects(LayoutClasses, max_level=max_level, greedy=greedy)

        return LayoutSlice(self.layout, filtered_layout_objects)

    def filter_by_widget(self, widget_type):
        """
        Returns a LayoutSlice pointing to fields with widgets of `widget_type`
        """
        self._check_layout_and_form()
        layout_field_names = self.layout.get_field_names()

        # Let's filter all fields with widgets like widget_type
        filtered_fields = []
        for pointer in layout_field_names:
            if isinstance(self.form.fields[pointer[1]].widget, widget_type):
                filtered_fields.append(pointer)

        return LayoutSlice(self.layout, filtered_fields)

    def exclude_by_widget(self, widget_type):
        """
        Returns a LayoutSlice pointing to fields with widgets NOT matching `widget_type`
        """
        self._check_layout_and_form()
        layout_field_names = self.layout.get_field_names()

        # Let's exclude all fields with widgets like widget_type
        filtered_fields = []
        for pointer in layout_field_names:
            if not isinstance(self.form.fields[pointer[1]].widget, widget_type):
                filtered_fields.append(pointer)

        return LayoutSlice(self.layout, filtered_fields)

    def __getitem__(self, key):
        """
        Return a LayoutSlice that makes changes affect the current instance of the layout
        and not a copy.
        """
        # when key is a string containing the field name
        if isinstance(key, string_types):
            # Django templates access FormHelper attributes using dictionary [] operator
            # This could be a helper['form_id'] access, not looking for a field
            if hasattr(self, key):
                return getattr(self, key)

            self._check_layout()
            layout_field_names = self.layout.get_field_names()

            filtered_field = []
            for pointer in layout_field_names:
                # There can be an empty pointer
                if len(pointer) == 2 and pointer[1] == key:
                    filtered_field.append(pointer)

            return LayoutSlice(self.layout, filtered_field)

        return LayoutSlice(self.layout, key)

    def __setitem__(self, key, value):
        self.layout[key] = value

    def __delitem__(self, key):
        del self.layout.fields[key]

    def __len__(self):
        if self.layout is not None:
            return len(self.layout.fields)
        else:
            return 0


class FormHelper(DynamicLayoutHandler, BaseLayout):
    """
    This class controls the form rendering behavior of the form passed to
    the `{% crispy %}` tag. For doing so you will need to set its attributes
    and pass the corresponding helper object to the tag::

        {% crispy form form.helper %}

    Let's see what attributes you can set and what form behaviors they apply to:

        **form_method**: Specifies form method attribute.
            You can see it to 'POST' or 'GET'. Defaults to 'POST'

        **form_action**: Applied to the form action attribute:
            - Can be a named url in your URLconf that can be executed via the `{% url %}` template tag. \
            Example: 'show_my_profile'. In your URLconf you could have something like::

                url(r'^show/profile/$', 'show_my_profile_view', name = 'show_my_profile')

            - It can simply point to a URL '/whatever/blabla/'.

        **form_id**: Generates a form id for dom identification.
            If no id provided then no id attribute is created on the form.

        **form_class**: String containing separated CSS clases to be applied
            to form class attribute. The form will always have by default
            'uniForm' class.

        **form_tag**: It specifies if <form></form> tags should be rendered when using a Layout.
            If set to False it renders the form without the <form></form> tags. Defaults to True.

        **form_error_title**: If a form has `non_field_errors` to display, they
            are rendered in a div. You can set title's div with this attribute.
            Example: "Oooops!" or "Form Errors"

        **formset_error_title**: If a formset has `non_form_errors` to display, they
            are rendered in a div. You can set title's div with this attribute.

        **form_style**: Uni-form has two built in different form styles. You can choose
            your favorite. This can be set to "default" or "inline". Defaults to "default".

    Public Methods:

        **add_input(input)**: You can add input buttons using this method. Inputs
            added using this method will be rendered at the end of the form/formset.

        **add_layout(layout)**: You can add a `Layout` object to `FormHelper`. The Layout
            specifies in a simple, clean and DRY way how the form fields should be rendered.
            You can wrap fields, order them, customize pretty much anything in the form.

    Best way to add a helper to a form is adding a property named helper to the form
    that returns customized `FormHelper` object::

        from crispy_forms.helper import FormHelper
        from crispy_forms.layout import Submit

        class MyForm(forms.Form):
            title = forms.CharField(_("Title"))

            @property
            def helper(self):
                helper = FormHelper()
                helper.form_id = 'this-form-rocks'
                helper.form_class = 'search'
                helper.add_input(Submit('save', 'save'))
                [...]
                return helper

    You can use it in a template doing::

        {% load crispy_forms_tags %}
        {% crispy form %}
    """
    form = None
    layout = None

    def __init__(self, layout=None, form=None, inputs=None):
        if layout is not None:
            self.layout = layout

        if inputs is not None:
            self.inputs = inputs

        if form is not None:
            self.form = getattr(form, 'form', form)

        if isinstance(self.form, type):
            self.form = self.form()

        if self.layout is None and self.form is not None:
            self.layout = self.build_default_layout(self.form)

    def build_default_layout(self, form):
        form = getattr(form, 'form', form)
        if isinstance(form, type):
            form = form()
        layout = Layout(*form.fields.keys())
        layout.add_input(Submit('submit', _("Submit")))
        return layout

    # def build_default_layout(self, form):
    #     # the import should be here to avoid a ciclic import requirement
    #     # TODO refactor create_layout to avoid the ciclic dependency
    #     import create_layout
    #     # TODO Ensure that this method is not called several times per class
    #     # If this is true, please put layout in a cache in form.__class__
    #     h = create_layout.create_form_helper(form, basehelper=self.__class__, helper=None)
    #     # print "build_default_layout", self.__class__, form.__class__, form.fields.keys()
    #     return h.layout

    def add_layout(self, layout):
        self.layout = layout
