# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
from django import forms
from django.test import TestCase

from nestedforms.forms import NestedForm, NestedModelForm, FormField, FormSetField, ModelFormField, ModelFormSetField, InlineFormField, InlineFormSetField, AutoDataFormMixin, AutoManagementFormMixin, BaseNestedFormSet

from .models import Cheese, Milk, Recipe, OtherIngredient
from .forms import NotRequiredForm, NotRequiredForm2, NotRequiredFormSet, RequiredFormSet, RequiredFormNotRequiredFormSet, RequiredFormRequiredFormSet, NotRequiredFormNotRequiredFormSet, NotRequiredFormRequiredFormSet, NotRequiredFormNotRequiredFormRequiredFormSet


class HTMLTestCase(TestCase):
    html_forms_dir = os.path.join(os.path.dirname(__file__), 'html_forms')

    def save_temp_html(self, filename, form_html):
        out_path = os.path.join('/tmp', filename)
        with open(out_path, 'w') as htmlout:
            htmlout.write(form_html)
        return out_path

    def get_cmp_form_html(self, filename):
        try:
            with open(filename) as form_file:
                form_html = form_file.read()
        except IOError:
            form_html = ''
        return form_html

    def assertHTMLFileEqual(self, html1, html_file, msg=None, **kwargs):
        filename = os.path.join(self.html_forms_dir, html_file)
        html2 = self.get_cmp_form_html(filename).format(**kwargs)
        if msg is None:
            msg = "%s is not equal to:\n%s" % (filename, html1)
        self.assertHTMLEqual(html1, html2, msg)

    def assertHTMLFileNotEqual(self, html1, html_file, msg=None, **kwargs):
        filename = os.path.join(self.html_forms_dir, html_file)
        html2 = self.get_cmp_form_html(filename).format(**kwargs)
        if msg is None:
            msg = "%s is not equal to:\n%s" % (filename, html1)
        self.assertHTMLNotEqual(html1, html2, msg)


class NestedFormsTestCase(HTMLTestCase):
    def test_nested_formfield(self):
        form = NotRequiredForm(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formfield-empty_form.html')

        # test the generated (empty) form
        form = NotRequiredForm(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formfield-empty_form.html')

        # test a valid form
        post = {
            'f1-n1': 'xxx',
            'f1-n2': 'yyy',
        }
        form = NotRequiredForm(post, auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formfield-initial.html')

        # test an initialised form
        initial = {
            'f1': {
                'n1': 'xxx',
                'n2': 'yyy',
            },
        }
        form = NotRequiredForm(initial=initial, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)  # because it isn't bound
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formfield-initial.html')

        # test an invalid form
        post = {}
        form = NotRequiredForm(post, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formfield-invalid.html')

    def test_nested_formfield_names(self):
        # test the generated (empty) form
        form = NotRequiredForm2(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formfield_names-empty_form.html')

        # test a valid form
        post = {
            'n1-n1': 'xxx',
            'n1-n2': 'yyy',
        }
        form = NotRequiredForm2(post, auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formfield_names-initial.html')

        # test an initialised form
        initial = {
            'n1': {
                'n1': 'xxx',
                'n2': 'yyy',
            },
        }  # This is ambiguous
        form = NotRequiredForm2(initial=initial, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)  # because it isn't bound
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formfield_names-initial.html')

        # test an invalid form
        post = {}
        form = NotRequiredForm2(post, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formfield_names-invalid.html')

    def test_nested_formsetfield(self):
        form = NotRequiredFormSet(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formsetfield-not_required.html')

        form = RequiredFormSet(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formsetfield-required.html')

        data_not_required_formset = {
            'f1': "xxx",
            'f2-TOTAL_FORMS': '1',
            'f2-INITIAL_FORMS': '0',
            'f2-MIN_NUM_FORMS': '0',
            'f2-MAX_NUM_FORMS': '1000',
        }
        self.assertTrue(NotRequiredFormSet(data_not_required_formset).is_valid())

        data_required_formset = {
            'f1': "xxx",
            'f2-TOTAL_FORMS': '2',
            'f2-INITIAL_FORMS': '0',
            'f2-MIN_NUM_FORMS': '1',
            'f2-MAX_NUM_FORMS': '1000',
        }
        self.assertFalse(RequiredFormSet(data_required_formset).is_valid())

    def _get_empty_post(self):
        return {
            'n2-f2-TOTAL_FORMS': '1',
            'n2-f2-INITIAL_FORMS': '0',
            'n2-f2-MIN_NUM_FORMS': '0',
            'n2-f2-MAX_NUM_FORMS': '1000',

            'o2-n2-f2-TOTAL_FORMS': '1',
            'o2-n2-f2-INITIAL_FORMS': '0',
            'o2-n2-f2-MIN_NUM_FORMS': '0',
            'o2-n2-f2-MAX_NUM_FORMS': '1000',
        }

    def _get_all_given_post(self):
        return {
            'n1': 'xxx',
            'n2-f1': 'yyy',
            'n2-f2-0-choice': 'a',
            'n2-f2-0-votes': '1',
            'n2-f2-1-choice': 'b',
            'n2-f2-1-votes': '2',
            'n2-f2-TOTAL_FORMS': '2',
            'n2-f2-INITIAL_FORMS': '0',
            'n2-f2-MIN_NUM_FORMS': '0',
            'n2-f2-MAX_NUM_FORMS': '1000',

            'o1': 'aaa',
            'o2-n1': 'xxx',
            'o2-n2-f1': 'yyy',
            'o2-n2-f2-0-choice': 'a',
            'o2-n2-f2-0-votes': '1',
            'o2-n2-f2-1-choice': 'b',
            'o2-n2-f2-1-votes': '2',
            'o2-n2-f2-TOTAL_FORMS': '2',
            'o2-n2-f2-INITIAL_FORMS': '0',
            'o2-n2-f2-MIN_NUM_FORMS': '0',
            'o2-n2-f2-MAX_NUM_FORMS': '1000',
        }

    def _get_missing_f1_post(self):
        return {
            'n1': 'xxx',
            'n2-f2-0-choice': 'a',
            'n2-f2-0-votes': '1',
            'n2-f2-1-choice': 'b',
            'n2-f2-1-votes': '2',
            'n2-f2-TOTAL_FORMS': '2',
            'n2-f2-INITIAL_FORMS': '0',
            'n2-f2-MIN_NUM_FORMS': '0',
            'n2-f2-MAX_NUM_FORMS': '1000',

            'o1': 'aaa',
            'o2-n1': 'xxx',
            'o2-n2-f2-0-choice': 'a',
            'o2-n2-f2-0-votes': '1',
            'o2-n2-f2-1-choice': 'b',
            'o2-n2-f2-1-votes': '2',
            'o2-n2-f2-TOTAL_FORMS': '2',
            'o2-n2-f2-INITIAL_FORMS': '0',
            'o2-n2-f2-MIN_NUM_FORMS': '0',
            'o2-n2-f2-MAX_NUM_FORMS': '1000'
        }

    def _get_missing_f2_post(self):
        return {
            'n1': 'xxx',
            'n2-f1': 'yyy',
            'n2-f2-TOTAL_FORMS': '1',
            'n2-f2-INITIAL_FORMS': '0',
            'n2-f2-MIN_NUM_FORMS': '0',
            'n2-f2-MAX_NUM_FORMS': '1000',

            'o1': 'aaa',
            'o2-n1': 'xxx',
            'o2-n2-f1': 'yyy',
            'o2-n2-f2-TOTAL_FORMS': '1',
            'o2-n2-f2-INITIAL_FORMS': '0',
            'o2-n2-f2-MIN_NUM_FORMS': '0',
            'o2-n2-f2-MAX_NUM_FORMS': '1000'
        }

    def _get_missing_f1_f2_post(self):
        return {
            'n1': 'xxx',
            'n2-f2-TOTAL_FORMS': '1',
            'n2-f2-INITIAL_FORMS': '0',
            'n2-f2-MIN_NUM_FORMS': '0',
            'n2-f2-MAX_NUM_FORMS': '1000',

            'o1': 'aaa',
            'o2-n1': 'xxx',
            'o2-n2-f2-TOTAL_FORMS': '1',
            'o2-n2-f2-INITIAL_FORMS': '0',
            'o2-n2-f2-MIN_NUM_FORMS': '0',
            'o2-n2-f2-MAX_NUM_FORMS': '1000'
        }

    def _get_all_initial(self):
        return {
            'n1': 'xxx',
            'n2': {
                'f1': 'yyy',
                'f2': [
                    {'choice': 'x', 'votes': 11},
                    {'choice': 'y', 'votes': 22},
                ],
            },
        }

    def test_not_required_form_not_required_formset(self):
        # TEST EMPTY
        # -----------
        form = NotRequiredFormNotRequiredFormSet(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_formset-empty_form.html')

        # TEST VALID POSTS
        # ----------------

        # all fields provided
        form = NotRequiredFormNotRequiredFormSet(self._get_all_given_post(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertEqual(form.changed_data, ['n1', 'n2'])
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_formset-all_given.html')

        # missing f1 and f2
        form = NotRequiredFormNotRequiredFormSet(self._get_missing_f1_f2_post(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_formset-missing_f1_f2.html')

        # missing f2
        form = NotRequiredFormNotRequiredFormSet(self._get_missing_f2_post(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_formset-missing_f2.html')

        # TEST WITH INITIAL DATA
        # ----------------------

        form = NotRequiredFormNotRequiredFormSet(initial=self._get_all_initial(), auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_formset-initialised_form.html')

        # TEST WITH INITIAL DATA + VALID POST
        # ----------------------

        form = NotRequiredFormNotRequiredFormSet(self._get_all_given_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertEqual(form.changed_data, ['n2'])
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_formset-initial_valid.html')

        # TEST WITH INITIAL DATA + INVALID POST
        # ----------------------

        form = NotRequiredFormNotRequiredFormSet(self._get_empty_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertEqual(form.changed_data, ['n1', 'n2'])
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_formset-initial_invalid.html')

        # TEST INVALID FORMS
        # ----------------------
        # entirely empty
        form = NotRequiredFormNotRequiredFormSet(self._get_empty_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_formset-invalid_empty.html')

        # missing f1
        form = NotRequiredFormNotRequiredFormSet(self._get_missing_f1_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_formset-invalid_missing_f1.html')

    def test_required_form_not_required_formset(self):
        # NOTICE: the tests for empty and initialised forms are not included here,
        # as they have been tested in test_not_required_form_not_required_formset

        # TEST VALID POSTS
        # ----------------

        # all fields provided
        form = RequiredFormNotRequiredFormSet(self._get_all_given_post(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_not_required_formset-all_given.html')

        # missing f2
        form = RequiredFormNotRequiredFormSet(self._get_missing_f2_post(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_not_required_formset-missing_f2.html')

        # TEST WITH INITIAL DATA + VALID POST
        # ----------------------

        form = RequiredFormNotRequiredFormSet(self._get_all_given_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertEqual(form.nested_errors, {})
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_not_required_formset-initial_valid-all_given.html')

        # This test results in an invalid form because it removes f2 from a form which initially does have it.
        form = RequiredFormNotRequiredFormSet(self._get_missing_f2_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertEqual(form.nested_errors, {'n2': {'f2': [{'votes': ["This field is required."], 'choice': ["This field is required."]}]}})
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_not_required_formset-initial_valid-missing_f2.html')

        # TEST WITH INITIAL DATA + INVALID POST
        # ----------------------

        form = RequiredFormNotRequiredFormSet(self._get_empty_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertEqual(form.nested_errors, {'n1': ["This field is required."], 'n2': {'f1': ["This field is required."], 'f2': [{'votes': ["This field is required."], 'choice': ["This field is required."]}]}})
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_not_required_formset-initial_invalid_empty.html')

        form = RequiredFormNotRequiredFormSet(self._get_missing_f1_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertEqual(form.nested_errors, {'n2': {'f1': ["This field is required."]}})
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_not_required_formset-initial_invalid_missing_f1.html')

        # TEST INVALID FORMS
        # ----------------------

        # entirely empty
        form = RequiredFormNotRequiredFormSet(self._get_empty_post(), auto_id=False)
        self.assertEqual(form.nested_errors, {'n1': ["This field is required."], 'n2': {'f1': ["This field is required."]}})
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_not_required_formset-invalid_empty.html')

        # missing f1
        form = RequiredFormNotRequiredFormSet(self._get_missing_f1_post(), auto_id=False)
        self.assertEqual(form.nested_errors, {'n2': {'f1': ["This field is required."]}})
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_not_required_formset-invalid_missing_f1.html')

    def test_not_required_form_required_formset(self):
        # NOTICE: the tests for empty and initialised forms are not included here,
        # as they have been tested in test_not_required_form_not_required_formset

        # TEST VALID POSTS
        # ----------------

        # all fields provided
        form = NotRequiredFormRequiredFormSet(self._get_all_given_post(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_required_formset-all_given.html')

        # TEST WITH INITIAL DATA + VALID POST
        # ----------------------

        # all fields provided
        form = NotRequiredFormRequiredFormSet(self._get_all_given_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_required_formset-initial_valid-all_given.html')

        # TEST WITH INITIAL DATA + INVALID POST
        # ----------------------

        # entirely empty
        form = NotRequiredFormRequiredFormSet(self._get_empty_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_required_formset-initial_invalid_empty.html')

        # missing f1
        form = NotRequiredFormRequiredFormSet(self._get_missing_f1_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_required_formset-initial_invalid_missing_f1.html')

        # missing f2
        form = NotRequiredFormRequiredFormSet(self._get_missing_f2_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_required_formset-initial_invalid-missing_f2.html')

        # TEST INVALID FORMS
        # ----------------------

        # entirely empty
        form = NotRequiredFormRequiredFormSet(self._get_empty_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_required_formset-invalid_empty.html')

        # missing f1
        form = NotRequiredFormRequiredFormSet(self._get_missing_f1_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_required_formset-invalid_missing_f1.html')

        # missing f2
        form = NotRequiredFormRequiredFormSet(self._get_missing_f2_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)  # It's false because the f1 was filled (making the non-required form needed to validate)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_required_formset-invalid_missing_f2.html')

    def test_required_form_required_formset(self):
        # TEST VALID POSTS
        # ----------------

        # all fields provided
        form = RequiredFormRequiredFormSet(self._get_all_given_post(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_required_formset-all_given.html')

        # TEST WITH INITIAL DATA + VALID POST
        # ----------------------

        # all fields provided
        form = RequiredFormRequiredFormSet(self._get_all_given_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_required_formset-initial_valid-all_given.html')

        # TEST WITH INITIAL DATA + INVALID POST
        # ----------------------

        # entirely empty
        form = RequiredFormRequiredFormSet(self._get_empty_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_required_formset-initial_invalid_empty.html')

        # missing f1
        form = RequiredFormRequiredFormSet(self._get_missing_f1_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_required_formset-initial_invalid_missing_f1.html')

        # missing f2
        form = RequiredFormRequiredFormSet(self._get_missing_f2_post(), initial=self._get_all_initial(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_required_formset-initial_invalid-missing_f2.html')

        # TEST INVALID FORMS
        # ----------------------

        # entirely empty
        form = RequiredFormRequiredFormSet(self._get_empty_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_required_formset-invalid_empty.html')

        # missing f1
        form = RequiredFormRequiredFormSet(self._get_missing_f1_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_required_formset-invalid_missing_f1.html')

        # missing f2
        form = RequiredFormRequiredFormSet(self._get_missing_f2_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_required_form_required_formset-invalid_missing_f2.html')

    def test_not_required_form_not_required_form_required_formset(self):
        # TEST VALID POSTS
        # ----------------

        # all fields provided
        form = NotRequiredFormNotRequiredFormRequiredFormSet(self._get_all_given_post(), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_form_required_formset-all_given.html', form.as_p())

        # entirely empty
        form = NotRequiredFormNotRequiredFormRequiredFormSet(self._get_empty_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_form_required_formset-invalid_empty.html')

        # missing f1
        form = NotRequiredFormNotRequiredFormRequiredFormSet(self._get_missing_f1_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_form_required_formset-invalid_missing_f1.html')

        # missing f2
        form = NotRequiredFormNotRequiredFormRequiredFormSet(self._get_missing_f2_post(), auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_not_required_form_not_required_form_required_formset-invalid_missing_f2.html')

    def test_nested_modelformfield(self):
        class TestForm(NestedForm):
            f1 = forms.CharField()
            f2 = ModelFormField(Cheese)

        # test the generated (empty) form
        form = TestForm(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelformfield-empty_form.html')

        # test a valid form
        post = {
            'f1': 'xxx',
            'f2-cheese_name': 'yyy',
        }
        form = TestForm(post, auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelformfield-initial.html')

        # test saving the ModelFormField
        f2 = form.cleaned_data['f2']
        f2.save()
        self.assertEqual(Cheese.objects.get(id=f2.id), f2)

        # test an initialised form
        initial = {
            'f1': 'xxx',
            'f2': {'cheese_name': 'yyy'},
        }
        form = TestForm(initial=initial, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)  # because it isn't bound
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelformfield-initial.html')

        # test an invalid form
        post = {
            'f1': 'xxx',
        }
        form = TestForm(post, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelformfield-invalid.html')

    def test_django_modelformset(self):
        from django.forms.models import modelformset_factory

        ModelFormSet = modelformset_factory(
            Cheese,
            extra=2,
            min_num=1,
            validate_min=True
        )

        # TEST EMPTY FORM
        # ---------------

        form = ModelFormSet(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_django_modelformset.html')

        # TEST VALID POSTS
        # ----------------

        post = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-cheese_name': 'yyy',
            'form-1-cheese_name': 'zzz',
        }

        form = ModelFormSet(post, auto_id=False)
        self.assertTrue(form.is_valid())
        self.assertHTMLFileEqual(form.as_p(), 'test_django_modelformset-valid.html')

        # TEST SAVE
        # ----------------

        instances = form.save()
        self.assertTrue(Cheese.objects.filter(pk=instances[0].id).exists())

        # TEST INSTANCE
        # ----------------

        form = ModelFormSet(auto_id=False)
        self.assertFalse(form.is_valid())
        self.assertHTMLFileEqual(form.as_p(), 'test_django_modelformset-instance.html')

        # TEST INITIAL
        # ----------------

        initial = [
            {'cheese_name': 'aaa'},
            {'cheese_name': 'bbb'},
        ]
        form = ModelFormSet(initial=initial, auto_id=False)
        self.assertFalse(form.is_valid())
        self.assertHTMLFileEqual(form.as_p(), 'test_django_modelformset-initial.html')

        # TEST INVALID
        # -------------

        post = {
            'form-TOTAL_FORMS': '0',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
        }
        form = ModelFormSet(post, auto_id=False)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_form_errors(), ['Please submit 1 or more forms.'])
        self.assertHTMLFileEqual(form.as_p(), 'test_django_modelformset-invalid.html')

    def test_nested_modelformsetfield(self):
        class TestForm(NestedForm):
            f1 = forms.CharField()
            f2 = ModelFormSetField(Cheese)

        # TEST EMPTY FORM
        # ---------------

        form = TestForm(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelformsetfield-empty_form.html')

        # TEST VALID POSTS
        # ----------------

        # all fields provided
        post = {
            'f1': 'xxx',
            'f2-TOTAL_FORMS': '1',
            'f2-INITIAL_FORMS': '0',
            'f2-MIN_NUM_FORMS': '0',
            'f2-MAX_NUM_FORMS': '1000',
            'f2-0-cheese_name': 'yyy',
            'f2-1-cheese_name': 'zzz',
        }
        form = TestForm(post, auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelformsetfield-valid.html')

        # TEST SAVE
        # ---------
        form.fields['f2'].save()
        f2 = form.cleaned_data['f2'][0]
        self.assertTrue(Cheese.objects.filter(id=f2.pk).exists())

        # TEST INITIAL
        # ----------------

        # initialise with dictionary
        initial = {
            'f1': 'xxx',
            'f2': [
                {'cheese_name': 'zzz'},
            ]
        }
        # Nested model formsets with initial values append those values if enough `extra`
        # forms are painted (and insofar as there is space allocated by `extra`.)
        form = TestForm(initial=initial, auto_id=False)
        self.assertHTMLFileEqual(
            form.as_p(),
            'test_nested_modelformsetfield-initial_dict.html',
            f2_0_id=f2.id,
        )

        # TEST OTHER VALID POSTS
        # ----------------

        # missing f2
        post = {
            'f1': 'xxx',
            'f2-TOTAL_FORMS': '1',
            'f2-INITIAL_FORMS': '0',
            'f2-MIN_NUM_FORMS': '0',
            'f2-MAX_NUM_FORMS': '1000'
        }
        form = TestForm(post, auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelformsetfield_invalid_missing_f2.html')

    def test_nested_inlineformsetfield(self):
        class TestForm(NestedModelForm):
            cheese = InlineFormField(Cheese)
            milk = InlineFormField(Milk)
            recipe = InlineFormSetField(OtherIngredient)

            class Meta:
                model = Recipe

        # test the generated (empty) form
        form = TestForm(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_inlineformsetfield-empty_form.html')

        # test a valid form (with all new items from the post, none from the database)
        post = {
            'cheese-cheese_name': 'xxx',
            'milk-milk_name': 'yyy',
            'salt': True,
            'recipe-TOTAL_FORMS': '4',
            'recipe-INITIAL_FORMS': '0',
            'recipe-MIN_NUM_FORMS': '0',
            'recipe-MAX_NUM_FORMS': '1000',
            'recipe-0-ingredient_name': 'aaa',
            'recipe-1-ingredient_name': 'bbb',
            'recipe-2-ingredient_name': 'ccc',
        }
        form = TestForm(post, auto_id=False)
        self.assertEqual(form.nested_errors, {})
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_inlineformsetfield-initial.html')

        # test saving the form
        recipe = form.save()
        ingredients = list(recipe.otheringredient_set.all())

        instance = Recipe.objects.get(id=recipe.id)
        self.assertEqual(recipe, instance)
        self.assertEqual(instance.cheese.id, recipe.cheese_id)
        self.assertEqual(instance.milk.id, recipe.milk_id)
        self.assertEqual(instance.otheringredient_set.count(), 3)

        # test an initialised form
        form = TestForm(instance=instance, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(
            form.as_p(),
            'test_nested_inlineformsetfield-instance.html',
            cheese_id=recipe.cheese_id,
            milk_id=recipe.milk_id,
            recipe_0_id=ingredients[0].id,
            recipe_1_id=ingredients[1].id,
            recipe_2_id=ingredients[2].id,
        )

        # test a edited form
        post = {
            'cheese-cheese_name': 'xxx',
            'cheese-id': recipe.cheese_id,
            'milk-milk_name': 'sss',  # changed
            'milk-id': recipe.milk_id,
            'salt': True,
            'recipe-TOTAL_FORMS': '6',
            'recipe-INITIAL_FORMS': '3',
            'recipe-MIN_NUM_FORMS': '0',
            'recipe-MAX_NUM_FORMS': '1000',
            'recipe-0-recipe': recipe.id,
            'recipe-0-id': ingredients[0].id,
            'recipe-0-ingredient_name': 'fff',  # changed
            'recipe-1-recipe': recipe.id,
            'recipe-1-id': ingredients[1].id,
            'recipe-1-ingredient_name': 'bbb',
            'recipe-2-recipe': recipe.id,
            'recipe-2-id': ingredients[2].id,
            'recipe-2-ingredient_name': 'ccc',
        }
        form = TestForm(post, instance=instance, auto_id=False)
        self.assertEqual(form.nested_errors, {})
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(
            form.as_p(),
            'test_nested_inlineformsetfield-edit-instance.html',
            cheese_id=recipe.cheese_id,
            milk_id=recipe.milk_id,
            recipe_0_id=ingredients[0].id,
            recipe_1_id=ingredients[1].id,
            recipe_2_id=ingredients[2].id,
        )

        # test saving the form
        recipe = form.save()

        instance = Recipe.objects.get(id=recipe.id)
        self.assertEqual(recipe, instance)
        self.assertEqual(instance.cheese.id, recipe.cheese_id)
        self.assertEqual(instance.milk.id, recipe.milk_id)
        self.assertEqual(instance.otheringredient_set.count(), 3)
        self.assertEqual(instance.cheese.cheese_name, "xxx")
        self.assertEqual(instance.milk.milk_name, "sss")

        # test an invalid form
        post = {
            'recipe-TOTAL_FORMS': '1',
            'recipe-INITIAL_FORMS': '0',
            'recipe-MIN_NUM_FORMS': '0',
            'recipe-MAX_NUM_FORMS': '1000',
        }
        form = TestForm(post, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_inlineformsetfield-invalid.html')

    def test_nested_modelform(self):
        class TestForm(NestedModelForm):
            cheese = InlineFormField(Cheese)
            milk = InlineFormField(Milk)

            class Meta:
                model = Recipe

        # test the generated (empty) form
        form = TestForm(auto_id=False)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelform-empty_form.html')

        # test a valid form
        post = {'cheese-cheese_name': "xxx", 'milk-milk_name': "yyy", 'salt': True}
        form = TestForm(post, auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelform-initial.html')

        # test saving the form
        recipe = form.save()
        self.assertEqual(Recipe.objects.get(id=recipe.id), recipe)

        # test an initialised form
        form = TestForm(instance=recipe, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)  # because it isn't bound
        self.assertHTMLFileEqual(
            form.as_p(),
            'test_nested_modelform-instance.html',
            cheese_id=recipe.cheese_id,
            milk_id=recipe.milk_id,
        )

        # test an initialised form ***
        post = {'cheese-cheese_name': "hhh", 'milk-milk_name': "iii", 'salt': False}
        form = TestForm(post, instance=Recipe(salt=True), auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)

        # test an invalid form
        post = {
            'cheese-cheese_name': "xxx",
            'salt': True,
        }
        form = TestForm(post, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_modelform-invalid.html')

    def test_nested_formfield_reentrance(self):
        post = {
            'f1-n1': 'xxx',
            'f1-n2': 'yyy',
        }
        form1 = NotRequiredForm(post)
        form2 = NotRequiredForm()

        # As of django 1.6, forms initialization deepcopy the field instance
        # during each instantiation of the form class. We expect and require
        # this behavior as field.widget is initialized with the initialized
        # (and perhaps data bound) nested form instance.
        self.assertNotEqual(id(form1.fields['f1']), id(form2.fields['f1']), "FormField object instance should be different")


class NestedFormsetsTestCase(HTMLTestCase):
    def test_nested_formsets(self):
        class CarSale(NestedForm):
            vin = forms.CharField(max_length=100)

        class Customs(NestedForm):
            agent_number = forms.CharField(max_length=100)

        class AnyOfComplement(NestedForm):
            carsale = FormField(CarSale, required=False)
            customs = FormField(Customs, required=False)

        class Complement(NestedForm):
            anyof = FormSetField(AnyOfComplement, min_num=0, validate_min=True, required=False)

        class Concept(NestedForm):
            description = forms.CharField(max_length=100)
            quantity = forms.CharField(max_length=100)
            value = forms.CharField(max_length=100)
            complement = FormField(Complement, required=False)

        class Concepts(NestedForm):
            concept = FormSetField(Concept, min_num=1, validate_min=True, required=True)

        class Invoice(NestedForm):
            serial = forms.CharField(max_length=100)
            concepts = FormField(Concepts, required=True)

        post = {
            'serial': '123456789',
            'concepts-concept-TOTAL_FORMS': '2',
            'concepts-concept-INITIAL_FORMS': '0',
            'concepts-concept-MIN_NUM_FORMS': '1',
            'concepts-concept-MAX_NUM_FORMS': '1000',
            'concepts-concept-0-description': 'first product',
            'concepts-concept-0-quantity': '1',
            'concepts-concept-0-value': '10.00',
            'concepts-concept-0-complement-anyof-TOTAL_FORMS': '1',
            'concepts-concept-0-complement-anyof-INITIAL_FORMS': '0',
            'concepts-concept-0-complement-anyof-MIN_NUM_FORMS': '0',
            'concepts-concept-0-complement-anyof-MAX_NUM_FORMS': '1000',
            'concepts-concept-0-complement-anyof-0-carsale-vin': '',
            'concepts-concept-1-description': '',
            'concepts-concept-1-quantity': '',
            'concepts-concept-1-value': '',
            'concepts-concept-1-complement-anyof-0-customs-agent_number': '',
            'concepts-concept-1-complement-anyof-TOTAL_FORMS': '1',
            'concepts-concept-1-complement-anyof-INITIAL_FORMS': '0',
            'concepts-concept-1-complement-anyof-MIN_NUM_FORMS': '0',
            'concepts-concept-1-complement-anyof-MAX_NUM_FORMS': '1000',
            'concepts-concept-1-complement-anyof-0-carsale-vin': '',
            'concepts-concept-1-complement-anyof-0-customs-agent_number': '',
        }

        form = Invoice(post)
        self.assertTrue(form.is_valid(), form.nested_errors)

    def test_nested_non_required_fields_in_required_form(self):
        class Bottom(NestedForm):
            nrf1 = forms.CharField(max_length=100, required=False)
            nrf2 = forms.CharField(max_length=100, required=False)
            nrf3 = forms.CharField(max_length=100, required=False)

        class Top(NestedForm):
            rf = forms.CharField(max_length=100, required=True)
            bfrm = FormField(Bottom, required=True)

        form = Top({'rf': 'XXX'})
        self.assertTrue(form.is_valid(), form.nested_errors)

    def test_nested_required_fields_in_non_required_nested_form(self):
        class Bottom1(NestedForm):
            b1nrf = forms.CharField(max_length=100, required=True)

        class Bottom2(NestedForm):
            b2nrf = forms.CharField(max_length=100, required=True)

        class Middle1(NestedForm):
            b1frm = FormField(Bottom1, required=True)

        class Middle2(NestedForm):
            b2frm = FormField(Bottom2, required=True)

        class Top(NestedForm):
            tf = forms.CharField(max_length=100, required=True)
            m1frm = FormField(Middle1, required=False)
            m2frm = FormField(Middle2, required=False)

        form = Top({'tf': 'aaa', 'm1frm-b1frm-b1nrf': 'xxx'})
        self.assertEqual(form.changed_data, ['tf', 'm1frm'])
        self.assertTrue(form.is_valid(), form.nested_errors)


class NestedFormsetsComplementoTestCase(HTMLTestCase):
    def test_nested_formsets(self):
        class BaseComprobanteFormSet(AutoManagementFormMixin, BaseNestedFormSet):
            pass

        class ComprobanteNestedForm(AutoDataFormMixin, NestedForm):
            pass

        class Ordenante(ComprobanteNestedForm):
            tipo_cuenta = forms.CharField(max_length=100, required=True)

        class Beneficiario(ComprobanteNestedForm):
            concepto = forms.CharField(max_length=100, required=True)

        class SpeiTercero(ComprobanteNestedForm):
            sello = forms.CharField(max_length=100, required=True)
            ordenante = FormField(Ordenante, required=True)
            beneficiario = FormField(Beneficiario, required=True)

        class VentaCombustible(ComprobanteNestedForm):
            num_permiso = forms.CharField(max_length=100, required=True)
            folio = forms.CharField(max_length=100, required=True)

        class ComplementoSpei(ComprobanteNestedForm):
            spei_tercero = FormSetField(SpeiTercero, min_num=1, validate_min=True, required=True, formset=BaseComprobanteFormSet)

        class AnyOf(ComprobanteNestedForm):
            venta_combustible = FormField(VentaCombustible, required=False)
            complemento_spei = FormField(ComplementoSpei, required=False)

        class Complemento(ComprobanteNestedForm):
            anyof = FormSetField(AnyOf, min_num=0, validate_min=True, required=False, formset=BaseComprobanteFormSet, extra=2)

        class Comprobante(ComprobanteNestedForm):
            forma_de_pago = forms.CharField(max_length=100, required=True)
            complemento = FormField(Complemento, required=False)

        form = AnyOf({'complemento_spei-spei_tercero-0-sello': ''}, auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)

        form = Comprobante({'forma_de_pago': 'CC'}, auto_id=False)
        self.assertTrue(form.is_valid(), form.nested_errors)
        self.assertHTMLFileEqual(form.as_p(), 'test_nested_formsets.html')
        self.assertEqual(form.nested_errors, {})

        form = Comprobante({'forma_de_pago': '', 'complemento-anyof-0-complemento_spei-spei_tercero-0-sello': 'sello'}, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)

        form = Comprobante({'forma_de_pago': ''}, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertEqual(form.nested_errors, {'forma_de_pago': ["This field is required."]})

        form = Comprobante({'forma_de_pago': 'CC', 'complemento-anyof-0-venta_combustible-num_permiso': 'ABC'}, auto_id=False)
        self.assertFalse(form.is_valid(), form.nested_errors)
        self.assertEqual(form.nested_errors, {'complemento': {'anyof': [{'venta_combustible': {'folio': ["This field is required."]}}, {}]}})
