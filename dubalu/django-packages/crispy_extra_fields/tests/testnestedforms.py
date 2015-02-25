# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
from django import forms
from django.test import TestCase, RequestFactory
from django.template.loader import render_to_string
from django.core import signing

request_factory = RequestFactory()

from lazyforms import views

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML

from ..layout import If, And, Or, Not, HasDataShallow, HasInitialShallow, HasChangedShallow, HasChanged

from nestedforms.forms import NestedForm, FormField, FormSetField, BaseNestedFormSet, AutoDataFormMixin, AutoManagementFormMixin


class FormB(AutoDataFormMixin, NestedForm):
    fB1 = forms.CharField(required=False)
    fB2 = forms.CharField(required=True)


class FormC(AutoDataFormMixin, NestedForm):
    fC1 = forms.CharField(required=False)
    fC2 = forms.CharField(required=False)


class FormA(AutoDataFormMixin, NestedForm):
    fA1 = forms.CharField(required=False)
    fA2 = FormField(FormB, required=False)
    fA3 = FormField(FormC, required=False)
    fA4 = forms.CharField(required=False)

    helper = FormHelper()
    helper.layout = Layout(
        If(
            HasInitialShallow('fA1', 'fA4'),
            Div(
                HTML("<p>fA1 and fA4 have initial</p>"),
                If(
                    HasChanged('fA2'),
                    'fA2',
                    HTML("<p>Load FormB (1)</p>"),
                ),
            ),
            Div(
                'fA1',
                If(
                    HasChanged('fA2'),
                    'fA2',
                    HTML("<p>Load FormB (2)</p>"),
                ),
                'fA4',
            )
        ),
        'fA3',
    )


class FormD(AutoDataFormMixin, NestedForm):
    fD1 = forms.CharField(required=False)
    fD2 = forms.CharField(required=False)
    fD3 = forms.CharField(required=False)


class BaseFormEFormSet(AutoManagementFormMixin, BaseNestedFormSet):
    helper = FormHelper()
    helper.layout = Layout(
        If(
            Not(HasInitialShallow('fE1')),
            'fE1',
            HTML("<p>fE1 has initial</p>")
        ),
        'fE2'
    )


class FormE(AutoDataFormMixin, NestedForm):
    fE1 = forms.CharField(required=False)
    fE2 = forms.CharField(required=False)


class MainTestingForm(AutoDataFormMixin, NestedForm):
    f1 = forms.CharField(required=False)
    f2 = forms.CharField(required=False)
    f3 = FormField(FormA, required=False)
    f4 = FormField(FormD, required=False)
    f5 = FormSetField(FormE, formset=BaseFormEFormSet, required=False)

    helper = FormHelper()
    helper.layout = Layout(
        'f1',
        'f2',
        'f3',
        If(
            HasChanged('f4'),
            'f4',
            HTML("<p>Load FormD</p>"),
        ),
        'f5',
    )


class HTMLTestCase(TestCase):
    html_forms_dir = os.path.join(os.path.dirname(__file__), 'html_forms')

    def save_temp_html(self, filename, form_html):
        out_path = os.path.join('/tmp', filename)
        with open(out_path, 'w') as htmlout:
            htmlout.write(form_html)
        return out_path

    def get_rendered(self, form):
        return render_to_string('crispy_extra_fields/crispy_template.html', {'form': form})


class NestedFormsTestCase(HTMLTestCase):
    def test_empty(self):
        """
        The initial for is displayed.
        """
        initial = {}
        POST = {}
        form = MainTestingForm(POST, initial=initial, auto_id=False)
        html = self.get_rendered(form)
        self.assertEqual(html.count('name="f3-fA2"'), 0, html)
        self.assertEqual(html.count('Load FormB (2)'), 1, html)
        self.assertEqual(html.count('name="f4-fD1"'), 0, html)
        self.assertEqual(html.count('Load FormD'), 1, html)

    def test_given_initial_fA1_fA4(self):
        """
        Assuming that two fields, namely fA1 and fA4, already have values.
        """
        initial = {'f3': {'fA1': 'aaa', 'fA4': 'bbb'}}
        POST = {}
        form = MainTestingForm(POST, initial=initial, auto_id=False)
        html = self.get_rendered(form)
        self.assertEqual(html.count('fA1 and fA4 have initial'), 1, html)
        self.assertEqual(html.count('Load FormB (1)'), 1, html)
        self.assertEqual(html.count('name="f4-fD1"'), 0, html)
        self.assertEqual(html.count('Load FormD'), 1, html)

    def test_given_initial_fA1_fA4_POST_fB1(self):
        """
        Assuming that two fields, namely fA1 and fA4, already have values.
        Additionally, the user is assumed to have loaded FormB via AJAX and
        added data to fB1, and finally posted the entire form.
        """
        initial = {'f3': {'fA1': 'aaa', 'fA4': 'bbb'}}
        POST = {'f3-fA2-fB1': 'xxx'}
        form = MainTestingForm(POST, initial=initial, auto_id=False)
        html = self.get_rendered(form)
        self.assertEqual(html.count('fA1 and fA4 have initial'), 1, html)
        self.assertEqual(html.count('fB1'), 1, html)
        self.assertEqual(html.count('xxx'), 1, html)
        self.assertEqual(html.count('Load FormD'), 1, html)

    def test_given_initial_fA1_fA4_f_POST_fB1(self):
        initial = {'f3': {'fA1': 'aaa', 'fA4': 'bbb'}, 'f5': [{'fE1': 'rrr'}, {'fE1': 'sss'}, {'fE2': 'ttt'}]}
        POST = {'f3-fA2-fB1': 'xxx'}
        form = MainTestingForm(POST, initial=initial, auto_id=False)
        html = self.get_rendered(form)
        self.assertEqual(html.count('fA1 and fA4 have initial'), 1, html)
        self.assertEqual(html.count('f3-fA2-fB1'), 1, html)
        self.assertEqual(html.count('xxx'), 1, html)
        self.assertEqual(html.count('fE1 has initial'), 2, html)
        self.assertEqual(html.count('ttt'), 1, html)

    def test_load_FormB_empty(self):
        form_class = FormB.__module__ + '.' + FormB.__name__
        prefix = 'f3-fA2'

        request = request_factory.get('/', data={})
        params = signing.dumps((form_class, None, prefix, None), compress=True)
        response = views.load(request, params)
        html = response.content

        self.assertEqual(html.count('name="f3-fA2-fB1"'), 1, html)
        self.assertEqual(html.count('name="f3-fA2-fB2"'), 1, html)

    def test_load_FormB_GET_POST(self):
        form_class = FormB.__module__ + '.' + FormB.__name__
        prefix = 'f3-fA2'

        request = request_factory.get('/', data={'f3-fA2-fB1': 'aaa'})
        params = signing.dumps((form_class, None, prefix, None), compress=True)
        response = views.load(request, params)
        html = response.content

        self.assertEqual(html.count('This field is required'), 0, html)

        request = request_factory.post('/', data={'f3-fA2-fB1': 'aaa'})
        params = signing.dumps((form_class, None, prefix, None), compress=True)
        response = views.load(request, params)
        html = response.content

        self.assertEqual(html.count('This field is required'), 1, html)

    def test_load_FormB_validate(self):
        form_class = FormB.__module__ + '.' + FormB.__name__
        prefix = 'f3-fA2'

        request = request_factory.get('/', data={'f3-fA2-fB1': 'aaa'})
        params = signing.dumps((form_class, None, prefix, None), compress=True)
        response = views.validate(request, params)
        html = response.content

        self.assertEqual(html, '{"f3-fA2-fB2": ["This field is required."]}', html)

    def test_load_FormD_empty(self):
        form_class = FormD.__module__ + '.' + FormD.__name__
        prefix = 'f4'

        request = request_factory.get('/', data={})
        params = signing.dumps((form_class, None, prefix, None), compress=True)
        response = views.load(request, params)
        html = response.content
        self.assertEqual(html.count('name="f4-fD1"'), 1, html)
        self.assertEqual(html.count('name="f4-fD2"'), 1, html)
        self.assertEqual(html.count('name="f4-fD3"'), 1, html)

    def test_load_FormE_GET(self):
        form_class = FormE.__module__ + '.' + FormE.__name__
        prefix = 'f5-10'
        request = request_factory.get('/', data={'f5-10-fE1': 'aaa', 'f5-10-fE2': 'bbb'})
        params = signing.dumps((form_class, None, prefix, None), compress=True)
        response = views.load(request, params)
        html = response.content

        self.assertEqual(html.count('name="f5-10-fE1"'), 1, html)
        self.assertEqual(html.count('name="f5-10-fE2"'), 1, html)

    def test_load_FormE_GET_formset(self):
        form_class = MainTestingForm.__module__ + '.' + MainTestingForm.__name__
        prefix = ''
        field = 'f5'
        request = request_factory.get('/', data={'f5-0-fE1': 'aaa', 'f5-0-fE2': 'bbb'})
        params = signing.dumps((form_class, field, prefix, None), compress=True)
        response = views.load(request, params)
        html = response.content

        self.assertEqual(html.count('name="f5-0-fE1"'), 1, html)
        self.assertEqual(html.count('value="aaa"'), 1, html)
        self.assertEqual(html.count('name="f5-0-fE2"'), 1, html)
        self.assertEqual(html.count('value="bbb"'), 1, html)
        # self.save_temp_html('temp.html', html)
