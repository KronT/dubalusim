# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import forms
from nestedforms.forms import NestedForm, FormField, FormSetField


class AnnotatedForm(NestedForm):
    n1 = forms.CharField(max_length=10, widget=forms.TextInput())
    n2 = forms.CharField(widget=forms.TextInput())


class NotRequiredForm(NestedForm):
    f1 = FormField(AnnotatedForm)


class NotRequiredForm2(NestedForm):
    n1 = FormField(AnnotatedForm)


class PlainForm(NestedForm):
    choice = forms.CharField()
    votes = forms.IntegerField()


class NotRequiredFormSet(NestedForm):
    f1 = forms.CharField()
    f2 = FormSetField(PlainForm, required=False)


class RequiredFormSet(NestedForm):
    f1 = forms.CharField()
    f2 = FormSetField(PlainForm, required=True)


class NotRequiredFormNotRequiredFormSet(NestedForm):
    n1 = forms.CharField()
    n2 = FormField(NotRequiredFormSet, required=False)


class RequiredFormNotRequiredFormSet(NestedForm):
    n1 = forms.CharField()
    n2 = FormField(NotRequiredFormSet, required=True)


class NotRequiredFormRequiredFormSet(NestedForm):
    n1 = forms.CharField()
    n2 = FormField(RequiredFormSet, required=False)


class RequiredFormRequiredFormSet(NestedForm):
    n1 = forms.CharField()
    n2 = FormField(RequiredFormSet, required=True)


class NotRequiredFormNotRequiredFormRequiredFormSet(NestedForm):
    o1 = forms.CharField()
    o2 = FormField(NotRequiredFormRequiredFormSet, required=False)
