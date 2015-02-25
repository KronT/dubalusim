################################################################################
# Snippet 2124 - "Autoconnect" model decorator, easy pre_save and post_save signal connection
from functools import wraps

from django.db.models import signals
from django.core.exceptions import ImproperlyConfigured


def autoconnect(model):
    """
    Class decorator that automatically connects pre_save / post_save signals on
    a model class to its pre_save() / post_save() methods.

    """
    if model._meta.abstract:
        raise ImproperlyConfigured('The model %s is abstract, so it '
              'cannot be autoconnected.' % model.__name__)

    def connect(attr):
        funcs = []
        for base in reversed(model.__mro__):
            func = getattr(base, attr, None)
            if func and func not in funcs:
                funcs.append(func)

        if funcs:
            def save_signal(sender, **kwargs):
                self = kwargs['instance']
                save = False
                for func in funcs:
                    if func(self, created=kwargs['created'], save=save):
                        save = True
                if save:
                    self.save()

            def signal(sender, **kwargs):
                self = kwargs['instance']
                for func in funcs:
                    func(self)

            if attr == 'post_save':
                wrapper = wraps(funcs[0])(save_signal)
            else:
                wrapper = wraps(funcs[0])(signal)

            getattr(signals, attr).connect(wrapper, sender=model)
            setattr(model, '_' + attr, wrapper)

    for attr in ('pre_save', 'post_save', 'pre_delete', 'post_delete'):
        connect(attr)

    return model
