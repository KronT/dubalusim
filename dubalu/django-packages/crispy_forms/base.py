# -*- coding: utf-8 -*-
from django.template import ContextPopException


def from_iterable(iterables):
    """
    Backport of `itertools.chain.from_iterable` compatible with Python 2.5
    """
    for it in iterables:
        for element in it:
            if isinstance(element, dict):
                for key in element:
                    yield key
            else:
                yield element


class KeepContext(object):
    """
    Context manager that receives a `django.template.Context` instance, tracks its changes
    and rolls them back when exiting the context manager, leaving the context unchanged.

    Layout objects can introduce context variables, that may cause side effects in later
    layout objects. This avoids that situation, without copying context every time.
    """
    def __init__(self, context):
        self.context = context

    def __enter__(self):
        self.context_dicts_len = len(self.context.dicts)
        self.context.push()

    def __exit__(self, type, value, traceback):
        if len(self.context.dicts) < self.context_dicts_len:
            raise ContextPopException
        self.context.dicts = self.context.dicts[:self.context_dicts_len]
