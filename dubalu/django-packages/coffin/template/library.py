from __future__ import absolute_import

import types
from copy import copy

from django.template.context import Context
from django.template import Library as DjangoLibrary, InvalidTemplateLibrary
from django.template.base import TemplateSyntaxError

from jinja2.ext import Extension as Jinja2Extension
from templatetag_sugar.register import extension_factory, node_factory, ASSIGNMENT_SYNTAX

from ..interop import DJANGO, JINJA2, guess_filter_type, jinja2_filter_to_django, django_filter_to_jinja2


__all__ = ['Library']


class Library(DjangoLibrary):
    """Version of the Django ``Library`` class that can handle both
    Django template engine tags and filters, as well as Jinja2
    extensions and filters.

    Tries to present a common registration interface to the extension
    author, but provides both template engines with only those
    components they can support.

    Since custom Django tags and Jinja2 extensions are two completely
    different beasts, they are handled completely separately. You can
    register custom Django tags as usual, for example:

        register.tag('current_time', do_current_time)

    Or register a Jinja2 extension like this:

        register.tag(CurrentTimeNode)

    Filters, on the other hand, work similarily in both engines, and
    for the most one can't tell whether a filter function was written
    for Django or Jinja2. A compatibility layer is used to make to
    make the filters you register usuable with both engines:

        register.filter('cut', cut)

    However, some of the more powerful filters just won't work in
    Django, for example if more than one argument is required, or if
    context- or environmentfilters are used. If ``cut`` in the above
    example where such an extended filter, it would only be registered
    with Jinja.

    See also the module documentation for ``coffin.interop`` for
    information on some of the limitations of this conversion.

    TODO: Jinja versions of the ``simple_tag`` and ``inclusion_tag``
    helpers would be nice, though since custom tags are not needed as
    often in Jinja, this is not urgent.
    """

    jinja2_filters = {}
    jinja2_extensions = []
    jinja2_environment_attrs = {}
    jinja2_globals = {}
    jinja2_tests = {}

    def __init__(self):
        super(Library, self).__init__()

    @classmethod
    def from_django(cls, django_library):
        """Create a Coffin library object from a Django library.

        Specifically, this ensures that filters already registered
        with the Django library are also made available to Jinja,
        where applicable.
        """
        result = cls()
        result.tags = copy(django_library.tags)
        for name, func in django_library.filters.iteritems():
            result._register_filter(name, func, type='django')
        return result

    def test(self, name=None, func=None):
        def inner(f):
            name = getattr(f, "_decorated_function", f).__name__
            self.jinja2_tests[name] = f
            return f
        if name is None and func is None:
            # @register.test()
            return inner
        elif func is None:
            if (callable(name)):
                # register.test()
                return inner(name)
            else:
                # @register.test('somename') or @register.test(name='somename')
                def dec(func):
                    return self.test(name, func)
                return dec
        elif name is not None and func is not None:
            # register.filter('somename', somefunc)
            self.jinja2_tests[name] = func
            return func
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to "
                "Library.test: (%r, %r)", (name, func))

    def object(self, name=None, func=None):
        def inner(f):
            name = getattr(f, "_decorated_function", f).__name__
            self.jinja2_globals[name] = f
            return f
        if name is None and func is None:
            # @register.object()
            return inner
        elif func is None:
            if (callable(name)):
                # register.object()
                return inner(name)
            else:
                # @register.object('somename') or @register.object(name='somename')
                def dec(func):
                    return self.object(name, func)
                return dec
        elif name is not None and func is not None:
            # register.object('somename', somefunc)
            self.jinja2_globals[name] = func
            return func
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to "
                "Library.object: (%r, %r)", (name, func))

    def tag(self, name=None, compile_function=None, environment={}):
        """Register a Django template tag (1) or Jinja 2 extension (2).

        For (1), supports the same invocation syntax as the original
        Django version, including use as a decorator.

        For (2), since Jinja 2 extensions are classes (which can't be
        decorated), and have the tag name effectively built in, only the
        following syntax is supported:

            register.tag(MyJinjaExtensionNode)

        If your extension needs to be configured by setting environment
        attributes, you can can pass key-value pairs via ``environment``.
        """
        if isinstance(name, type) and issubclass(name, Jinja2Extension):
            if compile_function:
                raise InvalidTemplateLibrary('"compile_function" argument not supported for Jinja2 extensions')
            self.jinja2_extensions.append(name)
            self.jinja2_environment_attrs.update(environment)
            return name
        else:
            if environment:
                raise InvalidTemplateLibrary('"environment" argument not supported for Django tags')
            return super(Library, self).tag(name, compile_function)

    def tag_function(self, func_or_node):
        if not isinstance(func_or_node, types.FunctionType) and \
                issubclass(func_or_node, Jinja2Extension):
            self.jinja2_extensions.append(func_or_node)
            return func_or_node
        else:
            return super(Library, self).tag_function(func_or_node)

    def jinja2_filter(self, *args, **kwargs):
        """Shortcut for filter(type='jinja2').
        """
        kw = {'type': JINJA2}
        kw.update(kwargs)
        return self.filter(*args, **kw)

    def filter(self, name=None, filter_func=None, type=None, jinja2_only=None, **flags):
        if name is None and filter_func is None:
            # @register.filter()
            def dec(func):
                return self.filter_function(func, type=type, jinja2_only=jinja2_only, **flags)
            return dec

        elif name is not None and filter_func is None:
            if callable(name):
                # @register.filter
                return self.filter_function(name, type=type, jinja2_only=jinja2_only, **flags)
            else:
                # @register.filter('somename') or @register.filter(name='somename')
                def dec(func):
                    return self.filter(name, func, type=type, jinja2_only=jinja2_only, **flags)
                return dec

        elif name is not None and filter_func is not None:
            # register.filter('somename', somefunc)
            for attr in ('expects_localtime', 'is_safe', 'needs_autoescape'):
                if attr in flags:
                    value = flags[attr]
                    # set the flag on the filter for FilterExpression.resolve
                    setattr(filter_func, attr, value)
                    # set the flag on the innermost decorated function
                    # for decorators that need it e.g. stringfilter
                    if hasattr(filter_func, "_decorated_function"):
                        setattr(filter_func._decorated_function, attr, value)
            filter_funcs = self._register_filter(name, filter_func, type=type, jinja2_only=jinja2_only)
            if not isinstance(filter_funcs, tuple):
                filter_funcs = (filter_funcs,)
            return filter_funcs[0]
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to "
                "Library.filter: (%r, %r)", (name, filter_func))

    def _register_filter(self, name, filter_func, type=None, jinja2_only=None):
        assert type in (None, JINJA2, DJANGO,)

        # The user might not specify the language the filter was written
        # for, but sometimes we can auto detect it.
        filter_type, can_be_ported = guess_filter_type(filter_func)
        assert not (filter_type and type) or filter_type == type or filter_type == JINJA2, \
            "guessed filter type (%s) not matching claimed type (%s) for %s.%s" % (
                filter_type, type, filter_func.__module__, filter_func.__name__,
            )
        if not filter_type and type:
            filter_type = type

        if filter_type == JINJA2:
            self.jinja2_filters[name] = filter_func
            if can_be_ported and not jinja2_only:
                self.filters[name] = jinja2_filter_to_django(filter_func)
            return filter_func

        elif filter_type == DJANGO:
            self.filters[name] = filter_func
            if not can_be_ported and jinja2_only:
                raise ValueError('This filter cannot be ported to Jinja2.')
            if can_be_ported:
                self.jinja2_filters[name] = django_filter_to_jinja2(filter_func)
            return filter_func

        else:
            django_func = jinja2_filter_to_django(filter_func)
            jinja2_func = django_filter_to_jinja2(filter_func)
            if jinja2_only:
                self.jinja2_filters[name] = jinja2_func
                return jinja2_func
            else:
                # register the filter with both engines
                self.filters[name] = django_func
                self.jinja2_filters[name] = jinja2_func
                return (django_func, jinja2_func)

    def simple_tag(self, func=None, takes_context=None, name=None):
        def dec(func):
            extension_cls = extension_factory(func, name, takes_context=takes_context)
            self.jinja2_extensions.append(extension_cls)
            return super(Library, self).simple_tag(None, takes_context, name)(func)
        if func is None:
            # @register.simple_tag(...)
            return dec
        elif callable(func):
            # @register.simple_tag
            return dec(func)
        else:
            raise TemplateSyntaxError("Invalid arguments provided to simple_tag")

    def assignment_tag(self, func=None, takes_context=None, name=None):
        def dec(func):
            extension_cls = extension_factory(func, name, ASSIGNMENT_SYNTAX, takes_context=takes_context)
            self.jinja2_extensions.append(extension_cls)
            return super(Library, self).assignment_tag(None, takes_context, name)(func)
        if func is None:
            # @register.assignment_tag(...)
            return dec
        elif callable(func):
            # @register.assignment_tag
            return dec(func)
        else:
            raise TemplateSyntaxError("Invalid arguments provided to assignment_tag")

    def inclusion_tag(self, file_name, context_class=Context, takes_context=False, name=None):
        def dec(func):
            extension_cls = extension_factory(func, name, inclusion_tag=file_name, takes_context=takes_context)
            self.jinja2_extensions.append(extension_cls)
            return super(Library, self).inclusion_tag(file_name, context_class, takes_context, name)(func)
        return dec

    def block_tag(self, func=None, takes_context=False, name=None):
        def dec(func):
            extension_cls = extension_factory(func, name, takes_context=takes_context, blocks=[])
            self.jinja2_extensions.append(extension_cls)
            node_cls = node_factory(func, name, takes_context=takes_context, blocks=[])
            compile_func = node_cls()
            function_name = (name or
                getattr(func, '_decorated_function', func).__name__)
            compile_func.__doc__ = func.__doc__
            self.tag(function_name, compile_func)
            return func
        if func is None:
            # @register.block_tag(...)
            return dec
        elif callable(func):
            # @register.block_tag
            return dec(func)
        else:
            raise TemplateSyntaxError("Invalid arguments provided to block_tag")

    def advanced_tag(self, func=None, syntax=None, blocks=None, inclusion_tag=None, needs_autoescape=False, takes_context=False, name=None):
        def dec(func):
            extension_cls = extension_factory(func, name, syntax=syntax, blocks=blocks, inclusion_tag=inclusion_tag, needs_autoescape=needs_autoescape, takes_context=takes_context)
            self.jinja2_extensions.append(extension_cls)
            node_cls = node_factory(func, name, syntax=syntax, blocks=blocks, inclusion_tag=inclusion_tag, needs_autoescape=needs_autoescape, takes_context=takes_context)
            compile_func = node_cls()
            function_name = (name or
                getattr(func, '_decorated_function', func).__name__)
            compile_func.__doc__ = func.__doc__
            self.tag(function_name, compile_func)
            return func
        if func is None:
            # @register.advanced_tag(...)
            return dec
        elif callable(func):
            # @register.advanced_tag
            return dec(func)
        else:
            raise TemplateSyntaxError("Invalid arguments provided to advanced_tag")
