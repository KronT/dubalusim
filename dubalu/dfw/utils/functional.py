# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from functools import wraps


class clsproperty(property):
    """
    Decorator that converts a method with a single ``cls`` argument into a
    class property.
    """
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        if fget is not None:
            fget = classmethod(fget)
        if fset is not None:
            fset = classmethod(fset)
        if fdel is not None:
            fdel = classmethod(fdel)
        super(clsproperty, self).__init__(fget, fset, fdel, doc)

    def __get__(self, instance, owner):
        if instance is not None:
            owner = instance.__class__
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        return self.fget.__get__(None, owner)()


class cached_clsproperty(clsproperty):
    """
    Decorator that converts a method with a single ``cls`` argument into a
    class property cached on the class object.
    """
    def __get__(self, instance, owner):
        if instance is not None:
            owner = instance.__class__
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        key = (owner, self.fget)
        try:
            cache = owner._cache
        except AttributeError:
            cache = owner._cache = {}
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.fget.__get__(None, owner)()
        return res


def memoize_method(func=None, num_args=None, in_class=False):
    """
    Wrap a function so that results for any argument tuple are stored in
    an attribute named after the method.
    Note that the args to the function must be usable as dictionary keys.

    Only the first num_args are considered when creating the key.
    """
    def _memoize_method(func):
        key = "_%s" % func.__name__

        @wraps(func)
        def wrapper(self, *args):
            if num_args is None:
                mem_args = args
            else:
                mem_args = args[:num_args]
            if in_class:
                obj = self.__class__
            else:
                obj = self
            try:
                cache = getattr(obj, key)
            except AttributeError:
                cache = {}
                setattr(obj, key, cache)
            if mem_args in cache:
                return cache[mem_args]
            result = func(self, *args)
            cache[mem_args] = result
            return result
        return wrapper

    if callable(func):
        return _memoize_method(func)
    return _memoize_method
