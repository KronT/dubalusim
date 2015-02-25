# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
from django import forms
from django.test import TestCase
from django.template.loader import render_to_string

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML

from ..layout import If, And, Or, Not, HasDataShallow, HasInitialShallow, HasChangedShallow


class HTMLTestCase(TestCase):
    html_forms_dir = os.path.join(os.path.dirname(__file__), 'html_forms')

    def get_rendered(self, form):
        return render_to_string('crispy_extra_fields/crispy_template.html', {'form': form})


class BaseTestingForm(forms.Form):
    field1 = forms.CharField(required=False)
    field2 = forms.CharField(required=False)
    field3 = forms.CharField(required=False)

    @property
    def helper(self):
        raise NotImplementedError

    def check_for_true(self, test):
        raise NotImplementedError

    def check_for_false(self, test):
        raise NotImplementedError


class BaseSimpleTestingForm(BaseTestingForm):

    def get_decision_func(self):
        raise NotImplementedError

    @property
    def helper(self):
        helper = FormHelper()
        helper.layout = Layout(
            Div(
                'field1',
                If(
                    self.get_decision_func(),
                    Div(
                        'field2',
                        'field3'
                    ),
                    Div(
                        HTML("<p>No initial</p>")
                    )
                )
            )
        )
        return helper

    def check_for_true(self, test):
        html = test.get_rendered(self)
        test.assertEqual(html.count('name="field1"'), 1, html)
        test.assertEqual(html.count('name="field2"'), 1, html)
        test.assertEqual(html.count('name="field3"'), 1, html)
        test.assertEqual(html.count('<p>No initial</p>'), 0, html)

    def check_for_false(self, test):
        html = test.get_rendered(self)
        test.assertEqual(html.count('name="field1"'), 1, html)
        test.assertEqual(html.count('name="field2"'), 0, html)
        test.assertEqual(html.count('name="field3"'), 0, html)
        test.assertEqual(html.count('<p>No initial</p>'), 1, html)


class BaseNestedTestingForm(BaseTestingForm):

    def get_decision_func1(self):
        raise NotImplementedError

    def get_decision_func2(self):
        raise NotImplementedError

    @property
    def helper(self):
        helper = FormHelper()
        helper.layout = Layout(
            Div(
                'field1',
                If(
                    self.get_decision_func1(),
                    Div(
                        'field2',
                        If(
                            self.get_decision_func2(),
                            Div(
                                'field3'
                            ),
                            Div(
                                HTML("<p>Missing field3</p>")
                            )
                        )
                    ),
                    Div(
                        HTML("<p>Missing field2</p>")
                    )
                )
            )
        )
        return helper

    def check_for_missing_field2(self, test):
        html = test.get_rendered(self)
        test.assertEqual(html.count('name="field1"'), 1, html)
        test.assertEqual(html.count('name="field2"'), 0, html)
        test.assertEqual(html.count('name="field3"'), 0, html)
        test.assertEqual(html.count('<p>Missing field2</p>'), 1, html)
        test.assertEqual(html.count('<p>Missing field3</p>'), 0, html)

    def check_for_missing_field3(self, test):
        html = test.get_rendered(self)
        test.assertEqual(html.count('name="field1"'), 1, html)
        test.assertEqual(html.count('name="field2"'), 1, html)
        test.assertEqual(html.count('name="field3"'), 0, html)
        test.assertEqual(html.count('<p>Missing field2</p>'), 0, html)
        test.assertEqual(html.count('<p>Missing field3</p>'), 1, html)

    def check_for_all(self, test):
        html = test.get_rendered(self)
        test.assertEqual(html.count('name="field1"'), 1, html)
        test.assertEqual(html.count('name="field2"'), 1, html)
        test.assertEqual(html.count('name="field3"'), 1, html)
        test.assertEqual(html.count('<p>Missing field2</p>'), 0, html)
        test.assertEqual(html.count('<p>Missing field3</p>'), 0, html)


class CrispyExtraFieldsSimpleTestCase(HTMLTestCase):
    def testIf_HasInitialShallow(self):
        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return HasInitialShallow('field2')

        # INITIAL EMPTY
        initial = {}
        form = TestingForm(initial=initial)
        form.check_for_false(self)

        # INITIAL INCOMPLETE
        initial = {'field1': 'aaa', 'field3': 'ccc'}
        form = TestingForm(initial=initial)
        form.check_for_false(self)

        # INITIAL GIVEN
        initial = {'field1': 'aaa', 'field2': 'bbb', 'field3': 'ccc'}
        form = TestingForm(initial=initial)
        form.check_for_true(self)

    def testIf_HasChangedShallow(self):
        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return HasChangedShallow('field2')

        # INITIAL & DATA EMPTY
        initial = {}
        POST = {}
        form = TestingForm(POST, initial=initial)
        form.check_for_false(self)

        # ONLY INITIAL INCOMPLETE
        initial = {'field1': 'aaa', 'field3': 'ccc'}
        POST = {}
        form = TestingForm(POST, initial=initial)
        form.check_for_false(self)

        # ONLY INITIAL GIVEN
        initial = {'field1': 'aaa', 'field2': 'bbb', 'field3': 'ccc'}
        POST = {}
        form = TestingForm(POST, initial=initial)
        form.check_for_true(self)

        # INITIAL = DATA
        initial = {'field1': 'aaa', 'field2': 'bbb', 'field3': 'ccc'}
        POST = {'field1': 'aaa', 'field2': 'bbb', 'field3': 'ccc'}
        form = TestingForm(POST, initial=initial)
        form.check_for_false(self)

        # INITIAL != DATA, BUT INITIAL['field2'] = DATA['field2']
        initial = {'field1': 'aaa', 'field2': 'bbb', 'field3': 'ccc'}
        POST = {'field1': 'rrr', 'field2': 'bbb', 'field3': 'ccc'}
        form = TestingForm(POST, initial=initial)
        form.check_for_false(self)

        # INITIAL != DATA AND INITIAL['field2'] != DATA['field2']
        initial = {'field1': 'aaa', 'field2': 'bbb', 'field3': 'ccc'}
        POST = {'field1': 'rrr', 'field2': 'xxx', 'field3': 'ccc'}
        form = TestingForm(POST, initial=initial)
        form.check_for_true(self)

    def test_Not(self):
        ftrue = lambda *args, **kargs: True

        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return Not(ftrue)
        form = TestingForm()
        form.check_for_false(self)

        ffalse = lambda *args, **kargs: False

        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return Not(ffalse)
        form = TestingForm()
        form.check_for_true(self)

    def test_Or(self):
        ftrue = lambda *args, **kargs: True
        ffalse = lambda *args, **kargs: False

        # TEST ALL FALSE
        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return Or(ffalse, ffalse)
        form = TestingForm()
        form.check_for_false(self)

        # TEST ONE TRUE
        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return Or(ftrue, ffalse)
        form = TestingForm()
        form.check_for_true(self)

        # TEST ALL TRUE
        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return Or(ftrue, ftrue)
        form = TestingForm()
        form.check_for_true(self)

    def test_And(self):
        ftrue = lambda *args, **kargs: True
        ffalse = lambda *args, **kargs: False

        # TEST ALL FALSE
        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return And(ffalse, ffalse)
        form = TestingForm()
        form.check_for_false(self)

        # TEST ONE TRUE
        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return And(ftrue, ffalse)
        form = TestingForm()
        form.check_for_false(self)

        # TEST ALL TRUE
        class TestingForm(BaseSimpleTestingForm):
            def get_decision_func(self):
                return And(ftrue, ftrue)
        form = TestingForm()
        form.check_for_true(self)


# class CrispyExtraFieldsNestedTestCase(HTMLTestCase):
#     def testIf_HasInitialShallow(self):
#         class TestingForm(BaseNestedTestingForm):
#             def get_decision_func1(self):
#                 return HasInitialShallow('field2')

#             def get_decision_func2(self):
#                 return HasInitialShallow('field3')

#         # INITIAL EMPTY
#         initial = {}
#         form = TestingForm(initial=initial)
#         form.check_for_missing_field2(self)

#         # INITIAL MISSING FIELD2
#         initial = {'field1': 'aaa', 'field3': 'ccc'}
#         form = TestingForm(initial=initial)
#         form.check_for_missing_field2(self)

#         # INITIAL MISSING FIELD3
#         initial = {'field1': 'aaa', 'field2': 'bbb'}
#         form = TestingForm(initial=initial)
#         form.check_for_missing_field3(self)

#         # INITIAL ALL
#         initial = {'field1': 'aaa', 'field2': 'bbb', 'field3': 'ccc'}
#         form = TestingForm(initial=initial)
#         form.check_for_all(self)
