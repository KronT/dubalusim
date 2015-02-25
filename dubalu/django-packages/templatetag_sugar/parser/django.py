from __future__ import absolute_import

import re
from collections import deque

from django.template import Node, Template
from django.template.loader import get_template, select_template
from django.utils.itercompat import is_iterable
from django.template import Context, TemplateSyntaxError as DjangoTemplateSyntaxError

from .base import Parser, BaseTagMixin


def type_value(token):
    if ':' in token:
        type, value = token.split(':', 1)
    else:
        type = token
        value = None
    return (type, value)


class DjangoParser(Parser):
    TOKEN_EOF = (None, None)
    ASSIGNMENT_RE = re.compile(r'^\w+=[^=]')

    def __init__(self, parser, token):
        self.parser = parser
        self._pushed = deque()
        self._history = deque(maxlen=100)
        self.pos = 0
        tokens = token.split_contents()
        self._add_tokens(tokens)

    def _add_tokens(self, tokens):
        self._history.append(('block_begin', 'block_begin'))
        for t in tokens:
            if self.ASSIGNMENT_RE.match(t):
                t = t.split('=')
                self._pushed.append(('name', t[0]))
                self._pushed.append(('assign', '='))
                t = t[1]
            if t[0] in ('"', "'") and t[0] == t[-1]:
                ty = t[0]
                t = t[1:-1]
                t = t.replace('\\' + ty, ty)  # Unescape
                self._pushed.append(('string', t))
            else:
                self._pushed.append(('name', t))
        self._pushed.append(('block_end', 'block_end'))
        try:
            self._current = self._pushed.popleft()
        except IndexError:
            self._current = self.TOKEN_EOF

    def __repr__(self):
        return "dj{%s <%s> %s}" % (' '.join(unicode(t[1]) for t in self._history), unicode(self._current[1]), ' '.join(unicode(t[1]) for t in self._pushed))

    @property
    def current(self):
        return self._current[1]

    def next(self):
        rv = self._current
        if self._pushed:
            self._current = self._pushed.popleft()
        elif self._current is not self.TOKEN_EOF:
            self._current = self.TOKEN_EOF
        self._history.append(rv)
        self.pos += 1
        return rv[1]

    def rewind(self, n=1):
        if n > self.pos:
            n = self.pos
        if n <= 0:
            return
        try:
            self._pushed.appendleft(self._current)
            for x in xrange(n - 1):
                token = self._history.pop()
                self._pushed.appendleft(token)
            self._current = self._history.pop()
            self.pos -= n
        except IndexError:
            self.fail('cannot rewind that far, rewind buffer overflow.')

    def test(self, token):
        type, value = type_value(token)
        if self._current[0] == type:
            if value is not None and self._current[1] != value:
                return False
            return True
        return False

    def expect(self, token):
        if not self.test(token):
            if self._current is self.TOKEN_EOF:
                self.fail('unexpected end of template, expected %r.' % token)
            raise self.fail("expected token %r, got %r" % (token, self._current))
        try:
            return self._current[1]
        finally:
            self.next()

    def fail(self, msg):
        raise DjangoTemplateSyntaxError(msg)

    def new_Body(self, tokens):
        self.next()
        tokens = tuple(type_value(token)[1] for token in tokens)
        body = self.parser.parse(tokens)
        self._history.append(('data', 'data'))
        token = self.parser.next_token()
        tokens = token.split_contents()
        self._add_tokens(tokens)
        return body

    def new_Expr(self):
        string = self._current[0] == 'string'
        if string:
            expr = '"%s"' % self.next().replace('"', '\\"')
        else:
            expr = self.expect('name')
        return self.parser.compile_filter(expr)

    def new_Store(self, value):
        return value

    def new_Name(self, value):
        return value

    def new_Pair(self, name, value):
        return (name, value)

    def new_Const(self, value):
        return value

    def new_List(self, value):
        return list(value)

    def new_Dict(self, value):
        return dict(value)


class BaseTagNode(Node, BaseTagMixin):
    def __init__(self, bodies=None, args=None, kwargs=None, asvars=None):
        self.bodies, self.args, self.kwargs, self.asvars = bodies, args, kwargs, asvars

    def __call__(self, parser, token):
        parser = DjangoParser(parser, token)
        return type(self)(*self.parse_tag(parser))

    def render(self, context):
        # Resolve arguments:
        args = []
        for value in self.args:
            if hasattr(value, 'resolve'):
                value = value.resolve(context, value)
            args.append(value)

        kwargs = {}
        for name, value in self.kwargs:
            if isinstance(value, dict):
                _kwargs = {}
                for _name, _value in value:
                    if hasattr(_value, 'resolve'):
                        _value = _value.resolve(context, _value)
                    _kwargs[_name] = _value
                kwargs[name] = _kwargs
            elif isinstance(value, list):
                _args = []
                for _value in value:
                    if hasattr(_value, 'resolve'):
                        _value = _value.resolve(context, _value)
                    _args.append(_value)
                kwargs[name] = _args
            else:
                if hasattr(value, 'resolve'):
                    value = value.resolve(context, value)
                kwargs[name] = value

        # Add body callables:
        first = True
        macro_caller = lambda b: lambda: b.render(context)
        for macro, body in self.bodies:
            macro_body = macro + '_body'
            if first:
                args.insert(0, macro_caller(body))
                first = False
            else:
                kwargs[macro_body] = macro_caller(body)

        # If context is required, add context:
        if self.takes_context:
            args.insert(0, context)

        # Call function:
        ret = self.function(*args, **kwargs)

        # For inclusion tags, render:
        if self.inclusion_tag and ret:
            _file_name = ret.get('file_name', self.inclusion_tag)
            if isinstance(_file_name, Template):
                t = _file_name
            elif not isinstance(_file_name, basestring) and is_iterable(_file_name):
                t = select_template(_file_name)
            else:
                t = get_template(_file_name)
            nodelist = t.nodelist
            new_context = Context(ret, **{
                'autoescape': context.autoescape,
                'current_app': context.current_app,
                'use_l10n': context.use_l10n,
                'use_tz': context.use_tz,
            })
            csrf_token = context.get('csrf_token', None)
            if csrf_token is not None:
                new_context['csrf_token'] = csrf_token
            ret = nodelist.render(new_context)

        # For assignable tags, assignment:
        if self.asvars:
            if len(self.asvars) > 1:
                for i, asvar in enumerate(self.asvars):
                    try:
                        context[asvar] = ret[i]
                    except IndexError:
                        context[asvar] = ''
            else:
                context[self.asvars[0]] = ret
            ret = ''
        return ret or ''
