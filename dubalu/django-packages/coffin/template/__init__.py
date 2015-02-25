from __future__ import absolute_import

from django.conf import settings
from django import template as django_template

from jinja2.runtime import Context as _Jinja2Context
from jinja2 import Template as _Jinja2Template, TemplateNotFound
TemplateDoesNotExist = TemplateNotFound

# Merge with ``django.template``.
__all__ = tuple(django_template.__all__)
del django_template.__all__
from django.template import *  # NOQA
django_template.__all__ = __all__
from django.test import signals

# Override default library class with ours
from .library import *  # NOQA
from .defaulttags import *  # NOQA


class Template(_Jinja2Template):
    '''Fixes the incompabilites between Jinja2's template class and
    Django's.

    The end result should be a class that renders Jinja2 templates but
    is compatible with the interface specfied by Django.

    This includes flattening a ``Context`` instance passed to render
    and making sure that this class will automatically use the global
    coffin environment.
    '''

    def __new__(cls, template_string, origin=None, name=None):
        # We accept the "origin" and "name" arguments, but discard them
        # right away - Jinja's Template class (apparently) stores no
        # equivalent information.
        from coffin.common import env

        return env.from_string(template_string, template_class=cls)

    def __iter__(self):
        # TODO: Django allows iterating over the templates nodes. Should
        # be parse ourself and iterate over the AST?
        raise NotImplementedError()

    def render(self, context=None):
        """Differs from Django's own render() slightly in that makes the
        ``context`` parameter optional. We try to strike a middle ground
        here between implementing Django's interface while still supporting
        Jinja's own call syntax as well.
        """
        if not isinstance(context, _Jinja2Context):
            context = self.new_context(context)
        ret = super(Template, self)._render(context)
        if settings.TEMPLATE_DEBUG:
            signals.template_rendered.send(sender=self, template=self, context=context)
        return ret

    @property
    def origin(self):
        return Origin(self.filename)


# libraries to load by default for a new environment
builtins = []


def add_to_builtins(module_name):
    """Add the given module to both Coffin's list of default template
    libraries as well as Django's. This makes sense, since Coffin
    libs are compatible with Django libraries.

    You can still use Django's own ``add_to_builtins`` to register
    directly with Django and bypass Coffin.

    Once thing that is special about Coffin is that because {% load %}
    is not supported in Coffin, *everything* it provides must be
    registered through the builtins.

    TODO: Allow passing path to (or reference of) extensions and
    filters directly. This would make it easier to use this function
    with 3rd party Jinja extensions that do not know about Coffin and
    thus will not provide a Library object.

    XXX/TODO: Why do we need our own custom list of builtins? Our
    Library object is compatible, remember!? We can just add them
    directly to Django's own list of builtins.
    """
    builtins.append(import_library(module_name))
    django_template.add_to_builtins(module_name)


add_to_builtins('coffin.template.defaulttags')
add_to_builtins('coffin.template.defaultfilters')
