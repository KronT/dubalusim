# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
from django import forms
from django.test import TestCase

from nestedforms.forms import NestedForm, FormSetField
#from pprint import pprint

class NestedFormsTestCase(TestCase):
    html_forms_dir = os.path.join(os.path.dirname(__file__), 'html_forms')

    def join_data(self, *args):
        new_data = {}
        for base_data in args:
            new_data.update(base_data)
        return new_data

    def get_data_manager(self, prefix, total_forms=1, initial_forms=0, min_num=0, max_num=1000):
        return {prefix + '-TOTAL_FORMS': total_forms, prefix + '-INITIAL_FORMS': initial_forms,
                prefix + '-MIN_NUM_FORMS': min_num, prefix + '-MAX_NUM_FORMS': max_num}

    def get_new_instance(self, parent_required, child_required, data):
        class SecondLevel(NestedForm):
            lev2a = forms.CharField()
            lev2b = forms.CharField()

        class FirstLevel(NestedForm):
            lev1a = forms.CharField()
            lev1b = FormSetField(SecondLevel, required=child_required)

        class Root(NestedForm):
            lev0a = forms.CharField()
            lev0b = FormSetField(FirstLevel, required=parent_required)

        return Root(data)

    def get_new_instance_count(self, parent_min_num, child_min_num, total_forms, data):
        base_data = self.get_data_manager('lev0b', total_forms=total_forms)
        for i in range(total_forms):
            b = self.get_data_manager('lev0b-%d-lev1b' % i, total_forms=total_forms)
            base_data.update(b)

        class SecondLevel(NestedForm):
            lev2a = forms.CharField()
            lev2b = forms.CharField()

        class FirstLevel(NestedForm):
            lev1a = forms.CharField()
            lev1b = FormSetField(SecondLevel, min_num=child_min_num, validate_min=True, max_num=1000, validate_max=True)

        class Root(NestedForm):
            lev0a = forms.CharField()
            lev0b = FormSetField(FirstLevel, min_num=parent_min_num, validate_min=True, max_num=1000, validate_max=True)

        data = self.join_data(data, base_data)
        #pprint(data)
        return Root(data)

    def test_nested_formsetfield(self):
        import sys
        sys.stdout = sys.stderr
        base_data = self.join_data(self.get_data_manager('lev0b'), self.get_data_manager('lev0b-0-lev1b'))
        for parent_required, child_required, data, expected_value in [
            (False, False, {'lev0a': 'something'}, True),
            (False, False, {}, False),
            (False, True, {'lev0a': 'something'}, True),
            (True, True, {'lev0a': 'something'}, False),
            (True, True, {'lev0a': 'something', 'lev0b-0-lev1a': 'VALUE-LEV1A'}, False),
            (True, True, {'lev0a': 'something',
                   'lev0b-0-lev1a': 'VALUE-LEV1A',
                   'lev0b-0-lev1b-0-lev2a': 'VALUE-LEV2A',
                   'lev0b-0-lev1b-0-lev2b': 'VALUE-LEV2B'}, True),
        ]:
            data = self.join_data(data, base_data)

            value = self.get_new_instance(parent_required, child_required, data)
            valid = value.is_valid()
            if expected_value:
                self.assertTrue(valid, locals())
            else:
                self.assertFalse(valid, locals())

    def test_nested_formsetfield_count(self):
        for parent_min_num, child_min_num, data, expected_value in [
            (0, 0, {'lev0a': 'something'}, True),
            (0, 0, {}, False),
            (0, 1, {'lev0a': 'something'}, True),
            (1, 1, {'lev0a': 'something'}, False),
            (1, 1, {'lev0a': 'something',
                    'lev0b-0-lev1a': 'VALUE-LEV1A'}, False),
            (1, 1, {'lev0a': 'something',
                    'lev0b-0-lev1a': 'VALUE-LEV1A',
                    'lev0b-0-lev1b-0-lev2a': 'VALUE-LEV2A',
                    'lev0b-0-lev1b-0-lev2b': 'VALUE-LEV2B'}, True),
        ]:
            value = self.get_new_instance_count(parent_min_num, child_min_num, 5, data)
            valid = value.is_valid()
            errmsg = "parent_min_num: %d, child_min_num: %d, expected_value: %s, valid: %s, data: %s" % (
                parent_min_num, child_min_num, expected_value, valid, data)
            if expected_value:
                self.assertTrue(valid, errmsg)
            else:
                self.assertFalse(valid, errmsg)
