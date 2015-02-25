# -*- coding: utf-8 -*-
"""
This is a Manager factory which allows for caching of objects in a model by
their primary key or label.

Example:
    from django.db import models

    class MyManager(models.Manager, CachedLabelManagerMixinFactory()):
        ...

    class MyModel(models.Model):
        ...
        objects = MyManager()

    ...

    # A second call to the next would return a cached object:
    MyModel.objects.get_for_pk(10)
"""
from __future__ import absolute_import, unicode_literals

import sys
import logging
import warnings

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from lru import LRUCache


logger = logging.getLogger('snippets.cached_label')


ENABLE_CACHES = getattr(settings, 'ENABLE_CACHES', True)
MEASURE_CACHES = getattr(settings, 'MEASURE_CACHES', False)


def create_cache(size):
    """
    Return the cache class for the given size.

    """
    if size == 0 or not ENABLE_CACHES:
        return None
    if size < 0:
        return {}
    return LRUCache(size)


def CachedLabelManagerMixinFactory(label_name='label', pk_name='pk', cache_name='_cache', cache_size=400, cache_misses=True):
    class CachedLabelManagerMixin(object):
        """
        Cache mixin for managers to avoid re-looking up objects all over the place.
        This cache is shared by all the get_for_* methods.

        """

        def get_for_label(self, label):
            """
            Lookup an object by label. Uses the same shared cache as get_for_pk.

            """
            if label is None:
                return None
            using = self.db
            _cache = getattr(self.__class__, cache_name, None) or {}
            try:
                _cache = _cache[using] or {}
                obj = _cache[label]
            except KeyError:
                try:
                    obj = self.get(**{label_name: label})
                except self.model.DoesNotExist:
                    if not cache_misses:
                        raise
                    obj = ObjectDoesNotExist
                    setattr(obj, label_name, label)
                self._add_to_cache(using, obj)
            if obj is ObjectDoesNotExist:
                raise self.model.DoesNotExist(
                    "%s matching query does not exist." %
                    self.model._meta.object_name)
            return obj

        def get_for_pk(self, pk):
            """
            Lookup an object by pk. Uses the same shared cache as get_for_label.

            """
            if pk is None:
                return None
            using = self.db
            _cache = getattr(self.__class__, cache_name, None) or {}
            try:
                _cache = _cache[using] or {}
                obj = _cache[pk]
            except KeyError:
                try:
                    obj = self.get(**{pk_name: pk})
                except self.model.DoesNotExist:
                    if not cache_misses:
                        raise
                    obj = ObjectDoesNotExist
                    setattr(obj, pk_name, pk)
                self._add_to_cache(using, obj)
            if obj is ObjectDoesNotExist:
                raise self.model.DoesNotExist(
                    "%s matching query does not exist." %
                    self.model._meta.object_name)
            return obj

        def get_or_create_for_pk(self, pk, defaults=None):
            if pk is None:
                return None, None
            using = self.db
            _cache = getattr(self.__class__, cache_name, None) or {}
            try:
                _cache = _cache[using] or {}
                obj, created = _cache[pk], False
            except KeyError:
                obj, created = self.get_or_create(pk=pk, defaults=defaults)
                self._add_to_cache(using, obj)
            return obj, created

        def fill_cache(self):
            using = self.db
            try:
                _cache = getattr(self.__class__, cache_name)
            except AttributeError:
                _cache = {}
                setattr(self.__class__, cache_name, _cache)
            try:
                _cache = _cache[using]
            except KeyError:
                _cache[using] = create_cache(cache_size)
                _cache = _cache[using]
            if _cache is not None:
                if '_all' not in _cache:
                    for obj in self.all():
                        self._add_to_cache(using, obj)
                    _cache['_all'] = True

        def _add_to_cache(self, using, obj):
            """Insert an object into the cache."""
            try:
                _cache = getattr(self.__class__, cache_name)
            except AttributeError:
                _cache = {}
                setattr(self.__class__, cache_name, _cache)
            try:
                _cache = _cache[using]
            except KeyError:
                _cache[using] = create_cache(cache_size)
                _cache = _cache[using]
            if _cache is not None:
                try:
                    _cache[getattr(obj, label_name)] = obj
                except AttributeError:
                    pass
                try:
                    _cache[getattr(obj, pk_name)] = obj
                except AttributeError:
                    pass
                if MEASURE_CACHES:
                    logger.info('%s.%s[%s] (%s) with %s keys in %s bytes (%s:%s)', self.__class__.__name__, cache_name, using, id(_cache), len(_cache.keys()), sys.getsizeof(_cache), getattr(obj, pk_name), getattr(obj, label_name))

        def clear_cache(self, instance=None):
            """
            Clear out the objects cache.

            """
            _cache = getattr(self.__class__, cache_name, None) or {}
            if instance is None:
                _cache.clear()
            else:
                using = instance._state.db
                try:
                    _cache = _cache[using] or {}
                except KeyError:
                    pass
                else:
                    try:
                        del _cache[getattr(instance, label_name)]
                    except KeyError:
                        pass
                    try:
                        del _cache[getattr(instance, pk_name)]
                    except KeyError:
                        pass

        def get_by_natural_key(self, label):
            warnings.warn("The get_for_id() method is now deprecated: use get_for_pk() instead.", PendingDeprecationWarning, stacklevel=2)
            return self.get_for_label(label)

        def get_for_id(self, pk):
            warnings.warn("The get_for_id() method is now deprecated: use get_for_pk() instead.", PendingDeprecationWarning, stacklevel=2)
            return self.get_for_pk(pk)

    return CachedLabelManagerMixin

CachedLabelManagerMixin = CachedLabelManagerMixinFactory()
