from __future__ import absolute_import

from jinja2.ext import Extension
from jinja2 import Undefined
from jinja2 import nodes

from .base import Parser, BaseTagMixin


class Jinja2Parser(Parser):
    def __init__(self, parser):
        self.parser = parser
        self._history = parser.stream._history
        self._pushed = parser.stream._pushed

    def __repr__(self):
        return "j2{%s <%s> %s}" % (' '.join(unicode(t) for t in self._history), unicode(self.current), ' '.join(unicode(t) for t in self._pushed))

    @property
    def pos(self):
        return self.parser.stream.pos

    @property
    def current(self):
        return self.parser.stream.current.value

    def next(self):
        rv = next(self.parser.stream)
        return rv.value

    def rewind(self, n=1):
        return self.parser.stream.rewind(n)

    def test(self, token):
        return self.parser.stream.current.test(token)

    def expect(self, token):
        return self.parser.stream.expect(token).value

    def fail(self, msg):
        self.parser.fail(msg)

    def new_Body(self, tokens):
        return self.parser.parse_statements(tokens)

    def new_Expr(self):
        return self.parser.parse_expression()

    def new_Store(self, value):
        return nodes.Name(value, 'store')

    def new_Name(self, value):
        return nodes.Name(value)

    def new_Pair(self, name, value):
        return nodes.Pair(name, value)

    def new_Const(self, value):
        return nodes.Const(value)

    def new_List(self, value):
        return nodes.List(value)

    def new_Dict(self, value):
        return nodes.Dict(value)


class BaseTagExtension(Extension, BaseTagMixin):
    def parse(self, parser):
        parser = Jinja2Parser(parser)
        bodies, args, kwargs, asvars = self.parse_tag(parser)

        ret = []

        # Add body macros:
        first = True
        for macro, body in bodies:
            macro_caller = '__' + macro + '_caller'
            macro_body = macro + '_body'
            ret.append(nodes.Macro(macro_caller, [], [], body))
            if first:
                args.insert(0, nodes.Name(macro_caller, 'load'))
                first = False
            else:
                kwargs.append(nodes.Pair(nodes.Const(macro_body), nodes.Name(macro_caller, 'load')))

        node = self.call_method('_function', args=[
            nodes.ContextReference(),
            nodes.List(args),
            nodes.Dict(kwargs),
        ])

        if self.needs_autoescape:
            node = nodes.MarkSafeIfAutoescape(node)

        # For assignable tags, assignment:
        if asvars:
            if len(asvars) > 1:
                _ret = nodes.Name('__ret', 'local')
                ret.append(nodes.Assign(_ret, node))
                for i, asvar in enumerate(asvars):
                    ret.append(nodes.Assign(asvar, nodes.Getitem(_ret, nodes.Const(i), 'load')))
            else:
                ret.append(nodes.Assign(asvars[0], node))
        else:
            ret.append(nodes.Output([node]))

        return ret

    def _function(self, context, args, kwargs):
        # If context is required, add context (as a django compatible context):
        if self.takes_context:
            args.insert(0, context)

        # Call function:
        _args = tuple(v if not isinstance(v, Undefined) else None for v in args)
        _kwargs = dict((k, v if not isinstance(v, Undefined) else None) for k, v in kwargs.items())
        # print '%s.%s(%s, %s)' % (self.function.__module__, self.function.__name__, [a if isinstance(a, basestring) else '<arg%s>' % i if i != 0 or not self.takes_context else '<context>' for i, a in enumerate(_args)], dict((k, '<arg>') for k in _kwargs.keys()))
        ret = self.function(*_args, **_kwargs)

        # For inclusion tags, render:
        if self.inclusion_tag and ret:
            _file_name = ret.get('file_name', self.inclusion_tag)
            template = self.environment.get_template(_file_name)
            ret = template.render(ret)
        return ret or ''
