# -*- coding: utf-8 -*-
# Copyright (c) 2011-2014 German M. Bravo (Kronuz)

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Snippet 2584: Django model objects and querysets dehydration/hydration

Dehydrates objects that can be dictionaries, lists or tuples containing django
model objects or django querysets. For each of those, it creates a
smaller/dehydrated version of it for saving in cache or pickling. The reverse
operation is also provided so dehydrated objects can also be re-hydrated.

Example::

    >>> from django.contrib.auth import get_user_model
    >>> UserModel = get_user_model()
    >>> from dehydration import hydrate, dehydrate
    >>> import pickle
    >>> users = list(UserModel.objects.all()[:20])
    >>> print repr(users)
    [<User: Indiana Jones>, <User: Bilbo Baggins>, <User: Lara Croft>, <User: Angus MacGyver>, <User: Luke Skywalker>, <User: Obi-Wan Kenobi>, ...]
    >>> pickled_users = pickle.dumps(users)
    >>> print len(pickled_users)
    17546
    >>> dehydrated_users = dehydrate(users)
    >>> pickled_dehydrated_users = pickle.dumps(dehydrated_users)
    >>> rehydrated_users = hydrate(pickle.loads(pickled_dehydrated_users))
    >>> print repr(rehydrated_users)
    [<User_Hydrated: Indiana Jones>, <User_Hydrated: Bilbo Baggins>, <User_Hydrated: Lara Croft>, <User_Hydrated: Angus MacGyver>, <User_Hydrated: Luke Skywalker>, <User_Hydrated: Obi-Wan Kenobi>, ...]
    >>> print len(pickled_dehydrated_users)
    1471
"""
import types

from django.db import models
from django.db.models.query import QuerySet
from django.utils.functional import LazyObject

########################################

from django.db.backends import util
from django.db.models.query_utils import DeferredAttribute


def transmogrify(cls, obj):
    """
    Upcast a class to a different type without asking questions.
    """
    # Run constructor, reassign values
    new = cls()
    for k, v in obj.__dict__.items():
        new.__dict__[k] = v
    new.pk = obj.pk
    return new


class HydratedAttribute(DeferredAttribute):
    def __get__(self, instance, owner):
        """
        Retrieves and caches the value from the datastore on the first lookup.
        Returns the cached value.
        """
        assert instance is not None
        if hasattr(instance, '_delayed_hydration'):
            instance = instance._delayed_hydration()
        elif hasattr(instance, '_hydrated_obj'):
            instance = instance._hydrated_obj
        else:
            instance = instance._hydrated_obj = transmogrify(self.model_ref(), instance)
        return getattr(instance, self.field_name)

    def __set__(self, instance, value):
        """
        Deferred loading attributes can be set normally (which means there will
        never be a database lookup involved.
        """
        if hasattr(instance, '_delayed_hydration'):
            instance = instance._delayed_hydration()
        elif hasattr(instance, '_hydrated_obj'):
            instance = instance._hydrated_obj
        else:
            instance = instance._hydrated_obj = transmogrify(self.model_ref(), instance)
        return setattr(instance, self.field_name, value)


def hydrated_class_factory(model, attrs):
    """
    Returns a class object that is a copy of "model" with the specified "attrs"
    being replaced with BulkDeferredAttribute objects. The "pk_value" ties the
    deferred attributes to a particular instance of the model.
    """
    class Meta:
        proxy = True
        app_label = model._meta.app_label

    # The app_cache wants a unique name for each model, otherwise the new class
    # won't be created (we get an old one back). Therefore, we generate the
    # name using the passed in attrs. It's OK to reuse an existing class
    # object if the attrs are identical.
    name = "%s_Hydrated_%s" % (model.__name__, '_'.join(sorted(list(attrs))))
    name = util.truncate_name(name, 80, 32)

    overrides = dict([(attr, HydratedAttribute(attr, model)) for attr in attrs])
    overrides["Meta"] = Meta
    overrides["__module__"] = model.__module__
    overrides["_deferred"] = True
    return type(str(name), (model,), overrides)

# The above function is also used to unpickle model instances with deferred
# fields.
hydrated_class_factory.__safe_for_unpickling__ = True


########################################

def _walk(obj, fnct, raise_exc=True, delayed=None, load_querysets=None, maxlevels=10, level=0, context=None):
    if context is None:
        context = {}
    if isinstance(obj, LazyObject):
        obj._setup()
        obj = obj._wrapped
    if not obj:
        return obj
    if maxlevels and level >= maxlevels:
        return obj
    objid = id(obj)
    if objid in context:
        return obj
    typ = type(obj)
    if typ is str:
        return obj
    if issubclass(typ, dict):
        if objid in context:
            return obj
        context[objid] = True
        dehydrated = False
        ret = {}
        for k, v in obj.items():
            val = _walk(v, fnct, raise_exc, delayed, load_querysets, maxlevels, level + 1, context)
            dehydrated = dehydrated or getattr(val, '_delayed_hydration', False)
            ret[k] = val
        del context[objid]
        return ret
    if issubclass(typ, list) or issubclass(typ, tuple) or issubclass(typ, set):
        context[objid] = True
        dehydrated = False
        ret = []
        for o in obj:
            val = _walk(o, fnct, raise_exc, delayed, load_querysets, maxlevels, level + 1, context)
            dehydrated = dehydrated or getattr(val, '_delayed_hydration', False)
            ret.append(val)
        del context[objid]
        if delayed is not None and dehydrated:
            if issubclass(typ, tuple):
                ret = tuple(ret)
            if issubclass(typ, set):
                ret = set(ret)
        else:
            if issubclass(typ, tuple):
                ret = tuple(ret)
            if issubclass(typ, set):
                ret = set(ret)
        return ret
    return fnct(obj, raise_exc, delayed, load_querysets)


class Dehydrated(object):
    def __init__(self, obj=None):
        if obj is not None:
            self._hydrated_obj = obj

    def __repr__(self):
        try:
            u = unicode(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = '[Bad Unicode data]'
        return str(u'<%s: %s>' % (self.__class__.__name__, u))

    def __str__(self):
        if hasattr(self, '__unicode__'):
            return unicode(self).encode('utf-8')
        return '%s object' % (self.__class__.__name__,)

    def __getstate__(self):
        obj_dict = self.__dict__.copy()
        obj_dict.pop('_model_class', None)
        obj_dict.pop('_hydrated_obj', None)
        return obj_dict


class DehydratedModel(Dehydrated):
    def __init__(self, obj=None, modelclass=None, pk=None):
        super(DehydratedModel, self).__init__(obj)
        if obj is None:
            __dict__ = {}
        else:
            __dict__ = obj.__dict__
            modelclass = obj.__class__
            pk = obj.pk
        self._model_class = modelclass
        if modelclass._deferred:
            modelclass = modelclass._meta.proxy_for_model
        self.app_label, self.object_name = modelclass._meta.app_label, modelclass.__name__
        if modelclass._meta.pk.attname != 'id':
            self.pk_attrname = modelclass._meta.pk.attname
        setattr(self, getattr(self, 'pk_attrname', 'id'), pk)
        self.data = self.filter_data(__dict__)

    def filter_data(self, data):
        modelclass = self.model_class()
        # Data should not and cannot return objects that are callable or descriptors:
        fields = set(k for k, v in modelclass.__dict__.items() if callable(v) or hasattr(v, '__get__'))
        if self.pk:
            fields.update(f.name for f in modelclass._meta.fields)
            return dict((k, v) for k, v in data.items() if k not in fields and not k.startswith('_') and not k.endswith('_id'))
        else:
            return dict((k, v) for k, v in data.items() if k not in fields and not k.startswith('_'))

    def __str__(self):
        if hasattr(self, '__unicode__'):
            return unicode(self).encode('utf-8')
        return '%s.%s.%s' % (self.app_label, self.object_name, self.pk)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.pk == other.pk

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.pk)

    def _get_pk_val(self, meta=None):
        return getattr(self, getattr(self, 'pk_attrname', 'id'), self.__dict__.get('pk'))  # Legacy

    def _set_pk_val(self, value):
        return setattr(self, getattr(self, 'pk_attrname', 'id'), value)

    pk = property(_get_pk_val, _set_pk_val)

    def model_class(self):
        if not hasattr(self, '_model_class'):
            self._model_class = models.get_model(self.app_label, self.object_name.split('_Deferred_')[0], only_installed=False)
        return self._model_class

    @staticmethod
    def delayed_hydrate(raise_exc, delayed, load_querysets, model_class=None):
        ret = False
        for modelclass, objects in delayed.items():
            if model_class is None or modelclass == model_class:
                pks = [pk for pk, objs in objects.items() if any(hasattr(obj, '_delayed_hydration') for obj in objs)]
                if pks:
                    if load_querysets and modelclass in load_querysets:
                        qs = load_querysets[modelclass]
                    else:
                        qs = modelclass._default_manager
                    for _obj in qs.filter(pk__in=pks):
                        obj, dobjs = objects[_obj.pk]
                        for dobj in dobjs:
                            dobj._hydrated_obj = _obj
                del delayed[modelclass]
                ret = True
        return ret

    def hydrate(self, raise_exc=True, delayed=None, load_querysets=None):
        if hasattr(self, '_hydrated_obj'):
            obj = self._hydrated_obj
        else:
            modelclass = self.model_class()
            if self.pk:
                if delayed is not None:
                    delayed.setdefault(modelclass, {})
                    if self.pk in delayed[modelclass]:
                        obj, dobjs = delayed[modelclass][self.pk]
                        dobjs.append(self)
                    else:
                        attrs = []
                        for field in modelclass._meta.fields:
                            if field.attname != modelclass._meta.pk.attname:
                                attrs.append(field.attname)
                        dehydrated_modelclass = hydrated_class_factory(modelclass, attrs)
                        obj = dehydrated_modelclass()
                        obj.__dict__[modelclass._meta.pk.attname] = self.pk
                        for parent in modelclass._meta.parents.values():
                            obj.__dict__[parent.rel.field_name] = self.pk
                        delayed[modelclass][self.pk] = (obj, [self])

                        def _delayed_hydration(self):
                            try:
                                return getattr(self, '_hydrated_obj')
                            except AttributeError:
                                self.delayed_hydrate(raise_exc, delayed, load_querysets, modelclass)
                            try:
                                return getattr(self, '_hydrated_obj')
                            except AttributeError:
                                msg = "%s matching query does not exist. Cannot hydrate model instance %s.%s.%s." % (
                                    modelclass._meta.object_name,
                                    modelclass._meta.app_label,
                                    modelclass._meta.object_name,
                                    self.pk,
                                )
                                raise modelclass.DoesNotExist(msg)
                        obj.__dict__['_delayed_hydration'] = types.MethodType(_delayed_hydration, self, modelclass)
                else:
                    obj = modelclass._default_manager.get(pk=self.pk)
                    self._hydrated_obj = obj
            else:
                obj = modelclass()
                self._hydrated_obj = obj
            if hasattr(self, 'data'):
                obj.__dict__.update(self.filter_data(self.data))
        return obj


class DehydratedQuerySet(Dehydrated):
    def __init__(self, qs):
        super(DehydratedQuerySet, self).__init__(qs)
        modelclass = qs.model
        if modelclass._deferred:
            modelclass = modelclass._meta.proxy_for_model
        self.app_label, self.object_name = modelclass._meta.app_label, modelclass.__name__
        self.query = qs.query

    @staticmethod
    def delayed_hydrate(raise_exc, delayed, load_querysets, model_class=None):
        pass

    def model_class(self):
        if not hasattr(self, '_model_class'):
            self._model_class = models.get_model(self.app_label, self.object_name.split('_Deferred_')[0], only_installed=False)
        return self._model_class

    def hydrate(self, raise_exc=True, delayed=None, load_querysets=None):
        if not hasattr(self, '_hydrated_obj'):
            modelclass = self.model_class()
            qs = modelclass._default_manager.all()
            qs.query = self.query
            self._hydrated_obj = qs
        return self._hydrated_obj


def _dehydrate(obj, raise_exc, all_delayed, load_querysets):
    typ = type(obj)
    if issubclass(typ, models.Model):
        return DehydratedModel(obj)
    if issubclass(typ, QuerySet):
        return DehydratedQuerySet(obj)
    return obj


def _hydrate(obj, raise_exc, all_delayed, load_querysets):
    typ = type(obj)
    if issubclass(typ, DehydratedModel):
        if all_delayed is not None:
            all_delayed.setdefault(DehydratedModel, {})
            delayed = all_delayed[DehydratedModel]
        return obj.hydrate(raise_exc, delayed, load_querysets)
    if issubclass(typ, DehydratedQuerySet):
        if all_delayed is not None:
            all_delayed.setdefault(DehydratedQuerySet, {})
            delayed = all_delayed[DehydratedQuerySet]
        return obj.hydrate(raise_exc, delayed, load_querysets)
    return obj


def dehydrate(obj, raise_exc=True):
    """
    Dehydrates objects containing django model objects and querysets.
    """
    return _walk(obj, _dehydrate, raise_exc)


def hydrate(obj, raise_exc=True, preloaded=None, load_querysets=None):
    """
    Hydrates objects containing dehydrated django model objects and querysets.
    """
    all_delayed = {}
    if preloaded is not None:
        for p in preloaded:
            if isinstance(p, LazyObject):
                p._setup()
                p = p._wrapped
            typ = type(p)
            if issubclass(typ, models.Model):
                if p.pk:
                    modelclass = p.__class__
                    if modelclass._deferred:
                        modelclass = modelclass._meta.proxy_for_model
                    all_delayed.setdefault(DehydratedModel, {})
                    delayed = all_delayed[DehydratedModel]
                    delayed.setdefault(modelclass, {})
                    delayed[modelclass][p.pk] = (p, [])
    return _walk(obj, _hydrate, raise_exc, all_delayed, load_querysets)
