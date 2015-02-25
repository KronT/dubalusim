from templatetag_sugar.parser import BaseTagNode, BaseTagExtension, Optional, Arguments, Assignment


ASSIGNMENT_SYNTAX = [Optional([Arguments(stop='as')]), 'as', Assignment()]


def tag(register, syntax=None, blocks=None, inclusion_tag=None, needs_autoescape=False, takes_context=False, name=None):
    def inner(func):
        if hasattr(register, 'jinja2_extensions'):
            extension_cls = extension_factory(func, name, syntax=syntax, blocks=blocks, inclusion_tag=inclusion_tag, needs_autoescape=needs_autoescape, takes_context=takes_context)
            register.jinja2_extensions.append(extension_cls)

        node_cls = node_factory(func, name, syntax=syntax, blocks=blocks, inclusion_tag=inclusion_tag, needs_autoescape=needs_autoescape, takes_context=takes_context)
        compile_func = node_cls()

        function_name = (name or
            getattr(func, '_decorated_function', func).__name__)

        compile_func.__doc__ = func.__doc__
        register.tag(function_name, compile_func)
        return func
    return inner


def _parser_factory(function, name='', syntax=None, blocks=None,
        inclusion_tag=None, takes_context=False, needs_autoescape=False,
        extension_name=None, factory_cls=None, suffix=''):

    tag_name = (name or
        getattr(function, '_decorated_function', function).__name__)

    if extension_name is None:
        extension_name = tag_name.title().replace('_', '') + 'Tag' + suffix

    attrs = {
        'tags': set([tag_name]),
        'function': staticmethod(function),
        'takes_context': takes_context,
        'inclusion_tag': inclusion_tag,
        'needs_autoescape': needs_autoescape,
    }

    if syntax is not None:
        attrs['syntax'] = syntax

    if blocks is not None:
        attrs['blocks'] = blocks

    extension_cls = type(bytes(extension_name), (factory_cls,), attrs)

    return extension_cls


def extension_factory(function, name='', syntax=None, blocks=None,
        inclusion_tag=None, takes_context=False, needs_autoescape=False,
        extension_name=None):
    return _parser_factory(function, name, syntax, blocks,
        inclusion_tag, takes_context, needs_autoescape,
        extension_name, BaseTagExtension, 'Extension')


def node_factory(function, name='', syntax=None, blocks=None,
        inclusion_tag=None, takes_context=False, needs_autoescape=False,
        extension_name=None):
    return _parser_factory(function, name, syntax, blocks,
        inclusion_tag, takes_context, needs_autoescape,
        extension_name, BaseTagNode, 'Node')
