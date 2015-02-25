# -*- coding: utf-8 -*-
"""
LRU cache utility class.

:author: Jinja Team.
:copyright: Copyright (c) 2014, deipi.com LLC. All Rights Reserved.
:copyright: Copyright (c) 2010 by the Jinja Team.
:license: BSD, see LICENSE for license details.

Changes:

This is different from Jinja's LRUCache in that it caches by type, so cached
values of different types are cached in different queues of the same capacity.

"""
from __future__ import absolute_import

from collections import deque
from threading import RLock


class LRUCache(object):
    """
    A type-based LRU Cache implementation.

    This is fast for small capacities (something below 1000) but doesn't scale.

    """

    def __init__(self, capacity):
        self.capacity = capacity
        self._wlock = RLock()
        self._mapping = {}
        self._queues = {}

    def __getstate__(self):
        return {
            'capacity': self.capacity,
            '_mapping': self._mapping,
            '_queues': self._queues,
        }

    def __setstate__(self, d):
        self.__dict__.update(d)

    def __getnewargs__(self):
        return (self.capacity,)

    def copy(self):
        """
        Return a shallow copy of the instance.

        """
        rv = self.__class__(self.capacity,)
        rv._mapping.update(self._mapping)
        rv._queues = dict((k, deque(v)) for k, v in self._queues)
        return rv

    def get(self, key, default=None):
        """
        Return an item from the cache dict or ``default``

        """
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        """
        Set ``default`` if the key is not in the cache otherwise
        leave unchanged. Return the value of this key.

        """
        with self._wlock:
            try:
                return self[key]
            except KeyError:
                self[key] = default
                return default

    def clear(self):
        """Clear the cache."""
        with self._wlock:
            self._mapping.clear()
            self._queues.clear()

    def __contains__(self, key):
        """Check if a key exists in this cache."""
        return key in self._mapping

    def __len__(self):
        """Return the current size of the cache."""
        return len(self._mapping)

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self._mapping
        )

    def __getitem__(self, key):
        """Get an item from the cache. Moves the item up so that it has the
        highest priority then.

        Raise a `KeyError` if it does not exist.
        """
        with self._wlock:
            value = self._mapping[key]
            queue = self._queues.setdefault(type(value), deque())
            if not len(queue) or queue[-1] != key:
                try:
                    queue.remove(key)
                except ValueError:
                    pass
                queue.append(key)
            return value

    def __setitem__(self, key, value):
        """
        Sets the value for an item. Moves the item up so that it
        has the highest priority then.

        """
        with self._wlock:
            try:
                del self[key]
            except KeyError:
                pass
            queue = self._queues.setdefault(type(value), deque())
            if len(queue) == self.capacity:
                del self._mapping[queue.popleft()]
            self._mapping[key] = value
            queue.append(key)

    def __delitem__(self, key):
        """
        Remove an item from the cache dict.
        Raise a ``KeyError`` if it does not exist.

        """
        with self._wlock:
            try:
                value = self._mapping[key]
            except KeyError:
                return
            queue = self._queues.setdefault(type(value), deque())
            try:
                queue.remove(key)
                if not len(queue):
                    del self._queues[type(value)]
            except ValueError:
                pass

    def items(self):
        """
        Return a list of items.

        """
        with self._wlock:
            result = [(key, self._mapping[key]) for key in self]
        result.reverse()
        return result

    def iteritems(self):
        """
        Iterate over all items.

        """
        return iter(self.items())

    def values(self):
        """
        Return a list of all values.

        """
        return [x[1] for x in self.items()]

    def itervalue(self):
        """
        Iterate over all values.

        """
        return iter(self.values())

    def keys(self):
        """
        Return a list of all keys ordered by most recent usage.

        """
        with self._wlock:
            result = [item for sublist in self._queues.values() for item in sublist]
        return result

    def iterkeys(self):
        """
        Iterate over all keys in the cache dict, ordered by
        the most recent usage.

        """
        return iter(self.keys())

    __iter__ = iterkeys

    def __reversed__(self):
        """
        Iterate over the values in the cache dict, oldest items
        coming first.

        """
        return reversed(self)

    __copy__ = copy


# register the LRU cache as mutable mapping if possible
try:
    from collections import MutableMapping
    MutableMapping.register(LRUCache)
except ImportError:
    pass
