# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _, ugettext
from django.template.defaultfilters import date

from crispy_forms.bootstrap import StrictButton, PrependedText, FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Span, Field

from crispy_extra_fields.layout import PrependedAppended, RawField


class InlineFormMixin(object):
    def get_submit_button_label(self):
        return _("Actualizar")

    def get_cancel_button_label(self):
        return _("cancelar")

    def get_submit_button_css_class(self):
        return 'btn-primary'

    @property
    def loadable_detail_helper(self):
        if not hasattr(self, '_loadable_detail_helper'):
            self._loadable_detail_helper = FormHelper()
            self._loadable_detail_helper.layout = Layout(
                self.get_detail_preamble(),
                self.get_formated_field(),
                self.get_loader(),
                form_show_labels=False,
                form_tag=False,
            )
        return self._loadable_detail_helper

    @property
    def detail_helper(self):
        if not hasattr(self, '_detail_helper'):
            self._detail_helper = FormHelper()
            self._detail_helper.layout = Layout(
                self.get_detail_preamble(),
                self.get_formated_field(),
                form_show_labels=False,
                form_tag=False,
            )
        return self._detail_helper

    def get_detail_preamble(self):
        return HTML("")

    def get_formated_field(self):
        raise NotImplementedError

    def get_loader(self):
        return self.get_loader_icon()

    def get_loader_icon(self):
        return HTML("""<a href="" class="loader" data-provide="lazy-loader"><i class="{0}"></i></a>""".format(self.get_loader_icon_class()))

    def get_loader_icon_class(self):
        return "fa fa-pencil"

    def get_loader_text(self):
        return HTML("""<a href="" class="loader" data-provide="lazy-loader">{0}</a>""".format(self.get_loader_text_label()))

    def get_loader_text_label(self):
        return _("editar")

    def get_input_group_class(self):
        return "col-sm-8"

    def get_valid_message(self):
        return None

    def get_invalid_message(self):
        return None


class InputFieldInlineForm(InlineFormMixin, forms.ModelForm):
    field_name = ''

    def get_formated_field(self):
        content = getattr(self.instance, self.field_name)
        if not content:
            field = self.fields.get(self.field_name)
            if field:
                content = '<span class="placeholder">{0}</span>'.format(field.label)
        return HTML("{0}&nbsp;".format(content))

    @property
    def edit_helper(self):
        if not hasattr(self, '_edit_helper'):
            self._edit_helper = FormHelper()
            self._edit_helper.layout = Layout(
                Div(
                    Div(
                        self.get_edit_label(),
                        PrependedAppended(
                            self.get_edit_preamble(),
                            RawField(self.field_name, **self.get_field_attrs()),
                            Span(
                                StrictButton(self.get_submit_button_label(), type='submit', css_class=self.get_submit_button_css_class()),
                                css_class='input-group-btn',
                            ),
                        ),
                        css_class=self.get_input_group_class()
                    ),
                    HTML("<a class='cancel' data-provide='cancel-edition' href="">{0}</a>".format(self.get_cancel_button_label())),
                    css_class="row",
                ),
                form_show_labels=False,
                form_tag=False,
            )
        return self._edit_helper

    def get_edit_preamble(self):
        return HTML("")

    def get_edit_label(self):
        return HTML("")

    def get_field_attrs(self):
        return {}


class IntegerFieldInlineForm(InputFieldInlineForm):
    def get_field_attrs(self):
        return dict(placeholder=_("Cantidad"))


class CharFieldInlineForm(InputFieldInlineForm):
    pass


class EmailFieldInlineForm(InputFieldInlineForm):
    def get_field_attrs(self):
        return dict(placeholder=_("Correo electrónico"))


class TextFieldInlineForm(InlineFormMixin, forms.ModelForm):
    field_name = ''

    def get_formated_field(self):
        content = getattr(self.instance, self.field_name)
        if not content:
            field = self.fields.get(self.field_name)
            if field:
                content = '<span class="placeholder">{0}</span>'.format(field.label)
        return HTML("{0}&nbsp;".format(content))

    @property
    def loadable_detail_helper(self):
        if not hasattr(self, '_loadable_detail_helper'):
            self._loadable_detail_helper = FormHelper()
            self._loadable_detail_helper.layout = Layout(
                self.get_detail_preamble(),
                self.get_loader(),
                self.get_formated_field(),
                form_show_labels=False,
                form_tag=False,
            )
        return self._loadable_detail_helper

    @property
    def detail_helper(self):
        if not hasattr(self, '_detail_helper'):
            self._detail_helper = FormHelper()
            self._detail_helper.layout = Layout(
                self.get_detail_preamble(),
                self.get_formated_field(),
                form_show_labels=False,
                form_tag=False,
            )
        return self._detail_helper

    @property
    def edit_helper(self):
        if not hasattr(self, '_edit_helper'):
            self._edit_helper = FormHelper()
            self._edit_helper.layout = Layout(
                Div(
                    Div(
                        self.get_edit_label(),
                        Field(self.field_name, **self.get_field_attrs()),
                        FormActions(
                            HTML('<ul>'),
                            HTML('<li>'),
                            StrictButton(
                                self.get_submit_button_label(),
                                type='submit',
                                css_class=self.get_submit_button_css_class(),
                            ),
                            HTML('</li><li>'),
                            HTML('<a class="cancel" data-provide="cancel-edition" href="">{0}</a>'.format(self.get_cancel_button_label())),
                            HTML('</li><ul>'),
                        ),
                    ),
                    css_class="row",
                ),
                form_show_labels=False,
                form_tag=False,
            )
        return self._edit_helper

    def get_edit_preamble(self):
        return HTML("")

    def get_edit_label(self):
        return HTML("")

    def get_detail_label(self):
        return HTML("")

    def get_submit_button_css_class(self):
        return 'btn btn-primary'


# class ValidatePasswordMixin(forms.Form):  # TODO: THIS HANS'T BEEN PROVED
#     password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

#     def __init__(self, *args, **kwargs):
#         self.user = kwargs.pop('user')
#         self.user_cache = None
#         super(ValidatePasswordMixin, self).__init__(*args, **kwargs)

#     def clean(self):
#         cleaned_data = super(ValidatePasswordMixin, self).clean()
#         if 'password' in cleaned_data:
#             self.user_cache = authenticate(self.user.email, cleaned_data['password'])

#             if self.user_cache is None:
#                 raise forms.ValidationError(
#                     _("Contraseña invália"),
#                 )
#         return cleaned_data

#     def get_user_id(self):
#         if self.user_cache:
#             return self.user_cache.id
#         return None

#     def get_user(self):
#         return self.user_cache


class ChangePasswordInlineForm(InlineFormMixin, forms.ModelForm):
    new_password1 = forms.CharField(label=_("New password"),
                                    widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"),
                                    widget=forms.PasswordInput)
    old_password = forms.CharField(label=_("Old password"),
                                   widget=forms.PasswordInput)
    error_messages = {
        'password_mismatch': _("Las dos contraseñas no coinciden."),
        'password_incorrect': _("Su contraseña actual es incorrecta. "
                                "Por favor, intente de nuevo."),
    }

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        return password2

    def clean_old_password(self):
        """
        Validates that the old_password field is correct.
        """
        old_password = self.cleaned_data["old_password"]
        if not self.instance.check_password(old_password):
            raise forms.ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )
        return old_password

    def save(self, commit=True):
        self.instance.set_password(self.cleaned_data['new_password1'])
        if commit:
            self.instance.save()
        return self.instance

    def get_formated_field(self):
        return HTML("*****&nbsp;")

    @property
    def edit_helper(self):
        if not hasattr(self, '_edit_helper'):
            self._edit_helper = FormHelper()
            self._edit_helper.layout = Layout(
                Div(
                    Div(
                        Div(
                            self.get_edit_preamble(),
                            PrependedText('old_password', '<i class="fa fa-key"></i>', **self.get_old_password_field_attrs()),
                            PrependedText('new_password1', '<i class="fa fa-key"></i>', **self.get_new_password1_field_attrs()),
                            PrependedText('new_password2', '<i class="fa fa-check"></i>', **self.get_new_password2_field_attrs()),
                            StrictButton(self.get_submit_button_label(), type='submit', css_class=self.get_submit_button_css_class()),
                        ),
                        css_class=self.get_input_group_class()
                    ),
                    HTML("<a class='cancel' data-provide='cancel-edition' href="">{0}</a>".format(self.get_cancel_button_label())),
                    css_class="row",
                ),
                form_show_labels=False,
                form_tag=True,
            )
        return self._edit_helper

    def get_old_password_field_attrs(self):
        return dict(placeholder=_("Current Password"))

    def get_new_password1_field_attrs(self):
        return dict(placeholder=_("New Password"))

    def get_new_password2_field_attrs(self):
        return dict(placeholder=_("Confirm Password"))

    def get_submit_button_css_class(self):
        return 'btn-primary pull-right'

    def get_edit_preamble(self):
        return HTML("")

    def get_input_group_class(self):
        return "col-sm-6"

    def get_invalid_message(self):
        return self.errors.values()[0]

    def get_valid_message(self):
        return ugettext("Su contraseña se actualizó exitosamente")


class DateRangeFieldsInlineForm(InlineFormMixin, forms.ModelForm):
    start_field_name = ''
    start_field_format = '%Y-%m-%d'

    end_field_name = ''
    end_field_format = '%Y-%m-%d'

    def __init__(self, *args, **kwargs):
        super(DateRangeFieldsInlineForm, self).__init__(*args, **kwargs)
        self.fields[self.start_field_name].widget.format = self.start_field_format
        self.fields[self.end_field_name].widget.format = self.end_field_format

    def get_formated_field(self):
        return HTML("{0} - {1}&nbsp;".format(date(getattr(self.instance, self.start_field_name)), date(getattr(self.instance, self.end_field_name))))

    @property
    def edit_helper(self):
        if not hasattr(self, '_edit_helper'):
            self._edit_helper = FormHelper()
            self._edit_helper.layout = Layout(
                Div(
                    Div(
                        Div(
                            PrependedAppended(
                                self.get_edit_preamble(),
                                RawField(self.start_field_name, **self.get_start_field_attrs()),
                                RawField(self.end_field_name, **self.get_end_field_attrs()),
                                Span(
                                    StrictButton(self.get_submit_button_label(), type='submit', css_class=self.get_submit_button_css_class()),
                                    css_class='input-group-btn',
                                ),
                            ),
                            css_class='input-daterange input-group',
                            data_provide='datepicker',
                        ),
                        css_class=self.get_input_group_class()
                    ),
                    HTML("<a class='cancel' data-provide='cancel-edition' href="">{0}</a>".format(self.get_cancel_button_label())),
                    css_class="row",
                ),
                form_show_labels=False,
                form_tag=True,
            )
        return self._edit_helper

    def get_start_field_attrs(self):
        return dict(placeholder=_("Inicio"), style="width: 50%;")

    def get_end_field_attrs(self):
        return dict(placeholder=_("Fin"), style="width: 50%;")

    def get_input_group_class(self):
        return "col-sm-10"

    def get_edit_preamble(self):
        return HTML("")
