# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from bisect import bisect_left, bisect_right


class Struct(dict):
    """
    Converts a dictionary to an object that has keys as attributes.

    >>> struct = Struct(a='first', b='second')
    >>> print struct.a
    ... 'first'

    >>> struct = Struct({'a': 'first', 'b': 'second'})
    >>> print struct.b
    ... 'second'

    [http://stackoverflow.com/questions/1305532/convert-python-dict-to-object]
    """
    exceptions = True

    def __getattr__(self, name):
        try:
            res = self[name]
            if isinstance(res, dict) and not isinstance(res, Struct):
                res = self[name] = self.__class__(res)
            return res
        except KeyError:
            if self.exceptions:
                raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))
            return self.__class__()

    def __setattr__(self, name, value):
        self[name] = value

    def copy(self):
        return self.__class__(dict.copy(self))


class SortedDictIndex(dict):
    """
    A dictionary with efficient access of key ranges

    Example:
    d = SortedDictIndex()
    ... the key-value pairs can be inserted in any order ...
    ... suppose you have the following dict ...
    {
    'A': 'v1', 'AA':  'v6', 'AAA': 'v11',
    'B': 'v2', 'BB':  'v7', 'BBB': 'v12',
    'C': 'v3', 'CC':  'v8', 'CCC': 'v13',
    'D': 'v4', 'DD':  'v9', 'DDD': 'v14',
    'E': 'v5', 'EE': 'v10', 'EEE': 'v15',
    }

    All functionality is provided by :method range:

    A single argument will retrieve all items with the given prefix
    In: list(D.range('BB'))
    Out: [('BB', 'v7'), ('BBB', 'v12')]

    If we specify two arguments :method range: retrieves all pairs
    inside the given range (inclusive bounds)

    In: list(D.range('BB', 'CCC'))
    Out: [('BB', 'v7'), ('BBB', 'v12'), ('C', 'v3'), ('CC', 'v8'), ('CCC', 'v13')]

    A keyword :param new_prefix: can be used to transform all matching keys into another key
         If :param new_prefix: is an string then the matching key will be replaced by new_prefix
            (well defined for single argument range queries)
         If :param new_prefix: is callable then the key is computed using the current key as follows
              new_key = new_prefix(old_key)


    In: list(D.range('BB', 'CCC', new_prefix=lambda p: 'new-' + p ))
    Out: [
       ('new-BB', 'v7'),
       ('new-BBB', 'v12'),
       ('new-C', 'v3'),
       ('new-CC', 'v8'),
       ('new-CCC', 'v13')
    ]

    Notice that :method range: returns an iterator object in all cases
    """
    _sorted_keys = None

    @property
    def sorted_keys(self):
        if self._sorted_keys is None:
            self._sorted_keys = self.keys()
            self._sorted_keys.sort()
        return self._sorted_keys

    def range(self, lo_prefix, hi_prefix=None, new_prefix=None):
        """
        Returns a list of key-value pairs having the given prefix. If new_prefix is given then
        the prefix is replaced by the new one

        If new_prefix is given then each matching key will be transformed as follows:
            If new_prefix is a callable object then the new key is generated as new_prefix(key)
            If new_prefix is a fixed length string then the first len(lo_prefix) characters of each key
            are replaced by new_prefix
        By default no transformation of key is applied

        """
        keys = self.sorted_keys
        lo = bisect_left(keys, lo_prefix)
        if hi_prefix is None:
            hi_prefix = lo_prefix
        # ~ symbol will work for strings with printable characters,
        # a much better way could be changing the default comparison but it will be pretty slow
        hi = bisect_right(keys, hi_prefix + "~")

        if new_prefix is None:
            for i in range(lo, hi):
                key = keys[i]
                yield (key, self[key])
        else:
            if callable(new_prefix):
                for i in range(lo, hi):
                    key = keys[i]
                    yield (new_prefix(key), self[key])
            else:
                s = len(lo_prefix)  # this will work for prefixes with fixed length
                for i in range(lo, hi):
                    _key = keys[i]
                    key = new_prefix + _key[s:]
                    yield (key, self[_key])

    def __setitem__(self, key, value):
        self._sorted_keys = None
        super(SortedDictIndex, self).__setitem__(key, value)

    def __delitem__(self, key):
        self._sorted_keys = None
        super(SortedDictIndex, self).__delitem__(key)

    def update(self, *args, **kwargs):
        self._sorted_keys = None
        return super(SortedDictIndex, self).update(*args, **kwargs)

    def pop(self, *args):
        self._sorted_keys = None
        return super(SortedDictIndex, self).pop(*args)

    def setdefault(self, key, default):
        if key not in self:
            self._sorted_keys = None
        return super(SortedDictIndex, self).setdefault(key, default)

    def clear(self):
        self._sorted_keys = None
        super(SortedDictIndex, self).clear()
