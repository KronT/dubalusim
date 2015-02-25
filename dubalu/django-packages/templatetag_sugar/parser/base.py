from __future__ import absolute_import

import itertools

from django.db.models.loading import get_model

from jinja2.exceptions import TemplateSyntaxError as JinjaTemplateSyntaxError
from django.template import TemplateSyntaxError as DjangoTemplateSyntaxError


class Parsable(object):
    pass


class NamedParsable(Parsable):
    def __init__(self, name=None, is_content=None):
        self.name = name
        self.is_content = is_content

    def syntax(self):
        if self.name:
            return "<%s:%s>" % (self._type, self.name)
        return "<%s>" % self._type


class Arguments(Parsable):
    min_num = 1
    max_num = None
    skip_commas = True
    plain_arguments = True
    as_arguments = False
    keyword_arguments = True

    def __init__(self, stop=None, min_num=None, max_num=None, skip_commas=None, plain_arguments=None, as_arguments=None, keyword_arguments=None, is_content=None):
        self.stop = ['block_end']
        if stop is not None:
            self.stop += ['name:' + s for s in stop]
        if min_num is not None:
            self.min_num = min_num
        if max_num is not None:
            self.max_num = max_num
        if skip_commas is not None:
            self.skip_commas = skip_commas
        if plain_arguments is not None:
            self.plain_arguments = plain_arguments
        if as_arguments is not None:
            self.as_arguments = as_arguments
        if keyword_arguments is not None:
            self.keyword_arguments = keyword_arguments
        self.is_content = is_content

    def syntax(self):
        all_args = []
        if self.plain_arguments:
            all_args.append('<expr>')
        if self.as_arguments:
            all_args.append('<expr> as <name>')
        if self.keyword_arguments:
            all_args.append('<name>=<expr>')
        if not all_args:
            args = '<...>'
        else:
            args = '|'.join(all_args)
        if not self.skip_commas:
            args += ','

        if self.min_num and self.max_num:
            min_max = '{%s,%s}' % (self.min_num, self.max_num)
        elif self.min_num:
            min_max = '{%s,}' % (self.min_num,)
        elif self.max_num:
            min_max = '{,%s}' % (self.max_num,)
        else:
            min_max = '{,}'

        if min_max == '{,}':
            args = '[%s...]' % args
        elif min_max == '{1,1}':
            if len(all_args) > 1:
                args = '(%s)' % args
        elif min_max == '{,1}':
            args = '[%s]' % args
        elif min_max == '{1,}':
            if len(all_args) > 1:
                args = '(%s)' % args
            args = '%s...' % args
        elif min_max.startswith('{1,'):
            if len(all_args) > 1:
                args = '(%s)' % args
            args = '%s [...%s]%s' % (args, min_max)
        else:
            if len(all_args) > 1:
                args = '(%s)' % args
            args = '%s%s' % (args, min_max)

        return args

    def parse(self, parser, args, kwargs, asvars, has_content, nxt=None, level=0):
        _args = []
        _kwargs = []
        plain_argument = False
        while not parser.test_any(*self.stop):
            _total = len(_args) + len(_kwargs)
            if _total:
                if self.skip_commas:
                    parser.skip_if('comma')
                else:
                    parser.expect('comma')
            if self.max_num and _total > self.max_num:
                parser.fail("can only define %s arguments" % self.max_num)

            if self.keyword_arguments and parser.test('name') and parser.look('assign'):
                name = parser.new_Const(parser.next())
                parser.next()
                value = parser.new_Expr()
                _kwargs.append(parser.new_Pair(name, value))
                plain_argument = False
            elif parser.test('name:as'):
                if self.as_arguments and plain_argument:
                    parser.next()
                    if not parser.test_any('name', 'string'):
                        parser.fail("no token name to set to using 'as', got %r" % parser.current)
                    plain_argument = False
                    name = parser.new_Const(parser.next())
                    value = _args.pop()
                    _kwargs.append(parser.new_Pair(name, value))
                else:
                    break
            else:
                _args.append(parser.new_Expr())
                plain_argument = True
        if plain_argument and not self.plain_arguments:
            parser.fail('no plain arguments expected')
        _total = len(_args) + len(_kwargs)
        if self.min_num and _total < self.min_num:
            parser.fail("you must define at least %s arguments" % self.min_num)
        if _kwargs:
            has_content = has_content or (self.is_content if self.is_content is not None else False)
        if _args:
            has_content = has_content or (self.is_content if self.is_content is not None else True)
        args.extend(_args)
        kwargs.extend(_kwargs)
        if nxt and not parser.test(nxt):
            parser.fail("expected token %r, got %r" % (nxt, parser.current))
        return args, kwargs, asvars, has_content


class Argument(Arguments):
    min_num = 1
    max_num = 1
    skip_commas = True
    plain_arguments = True
    as_arguments = False
    keyword_arguments = True


class Constant(NamedParsable):
    def __init__(self, text, name=None, is_content=None):
        self.text = text
        self.name = name
        self.is_content = is_content

    def syntax(self):
        return self.text

    def parse(self, parser, args, kwargs, asvars, has_content, nxt=None, level=0):
        name = parser.expect('name:' + self.text)
        if self.name:
            kwargs.append(parser.new_Pair(parser.new_Const(self.name), parser.new_Const(name)))
            has_content = has_content or (self.is_content if self.is_content is not None else False)
        else:
            has_content = has_content or (self.is_content if self.is_content is not None else False)
        if nxt and not parser.test(nxt):
            parser.fail("expected token %r, got %r" % (nxt, parser.current))
        return args, kwargs, asvars, has_content


class Name(NamedParsable):
    _type = 'name'

    def parse(self, parser, args, kwargs, asvars, has_content, nxt=None, level=0):
        value = parser.new_Const(parser.expect('name'))
        if self.name:
            kwargs.append(parser.new_Pair(parser.new_Const(self.name), value))
            has_content = has_content or (self.is_content if self.is_content is not None else False)
        else:
            args.append(value)
            has_content = has_content or (self.is_content if self.is_content is not None else True)
        if nxt and not parser.test(nxt):
            parser.fail("expected token %r, got %r" % (nxt, parser.current))
        return args, kwargs, asvars, has_content


class Variable(NamedParsable):
    _type = 'expr'

    def parse(self, parser, args, kwargs, asvars, has_content, nxt=None, level=0):
        value = parser.new_Expr()
        if self.name:
            kwargs.append(parser.new_Pair(parser.new_Const(self.name), value))
            has_content = has_content or (self.is_content if self.is_content is not None else False)
        else:
            args.append(value)
            has_content = has_content or (self.is_content if self.is_content is not None else True)
        if nxt and not parser.test(nxt):
            parser.fail("expected token %r, got %r" % (nxt, parser.current))
        return args, kwargs, asvars, has_content


class Assignment(NamedParsable):
    _type = 'asvar'

    def __init__(self, name=None, is_content=None, asvar=None):
        self.name = name
        self.is_content = is_content
        self.asvar = asvar

    def parse(self, parser, args, kwargs, asvars, has_content, nxt=None, level=0):
        if self.asvar:
            name = self.asvar
            value = parser.new_Const(name)
        else:
            if not parser.test_any('name', 'string'):
                parser.fail("expected assignment token, got %r" % parser.current)
            name = parser.next()
            value = parser.new_Const(name)
        asvars.append(parser.new_Store(name))
        if self.name:
            kwargs.append(parser.new_Pair(parser.new_Const(self.name), value))
            has_content = has_content or (self.is_content if self.is_content is not None else False)
        else:
            has_content = has_content or (self.is_content if self.is_content is not None else False)
        if nxt and not parser.test(nxt):
            parser.fail("expected token %r, got %r" % (nxt, parser.current))
        return args, kwargs, asvars, has_content


class AssignmentVariable(Assignment):
    _type = 'asvar'

    def parse(self, parser, args, kwargs, asvars, has_content, nxt=None, level=0):
        if self.asvar:
            name = self.asvar
            value = parser.new_Const(name)
        else:
            if not parser.test_any('name', 'string'):
                parser.fail("expected assignment token, got %r" % parser.current)
            name = parser.current
            value = parser.new_Expr()
        asvars.append(parser.new_Store(name))
        if self.name:
            kwargs.append(parser.new_Pair(parser.new_Const(self.name), value))
            has_content = has_content or (self.is_content if self.is_content is not None else False)
        else:
            args.append(value)
            has_content = has_content or (self.is_content if self.is_content is not None else True)
        if nxt and not parser.test(nxt):
            parser.fail("expected token %r, got %r" % (nxt, parser.current))
        return args, kwargs, asvars, has_content


class Model(NamedParsable):
    _type = 'model'

    def parse(self, parser, args, kwargs, asvars, has_content, nxt=None, level=0):
        app = parser.expect('name')
        parser.expect('dot')
        model = parser.expect('name')
        value = parser.new_Const(get_model(app, model))
        if self.name:
            kwargs.append(parser.new_Pair(parser.new_Const(self.name), value))
            has_content = has_content or (self.is_content if self.is_content is not None else False)
        else:
            args.append(value)
            has_content = has_content or (self.is_content if self.is_content is not None else True)
        if nxt and not parser.test(nxt):
            parser.fail("expected token %r, got %r" % (nxt, parser.current))
        return args, kwargs, asvars, has_content


class Blocks(Parsable):
    def __init__(self, *all_parts, **kwargs):
        if 'nxt' in kwargs:
            self.nxt = kwargs['nxt']
        if 'multiple' in kwargs:
            self.multiple = kwargs['multiple']
        self.name = kwargs.get('name')
        self.max_num = kwargs.get('max_num', 1)
        self.min_num = kwargs.get('min_num', 1)
        self.all_parts = all_parts or None

    def _syntax(self, parts):
        if len(self.all_parts) > 1:
            if self.optional:
                fmt = "%s"
            else:
                fmt = "%s"
        else:
            if self.optional:
                fmt = "%s"
            else:
                fmt = "%s"
        return fmt % (" ".join((Constant(part) if isinstance(part, basestring) else part).syntax() for part in parts))

    def syntax(self):
        if len(self.all_parts) > 1:
            if self.optional:
                fmt = "[%s]"
            else:
                fmt = "(%s)"
        else:
            if self.optional:
                fmt = "[%s]"
            else:
                fmt = "%s"
        return fmt % "|".join(self._syntax(parts) for parts in self.all_parts)

    def parse(self, parser, args, kwargs, asvars, has_content, nxt=None, level=0):
        pos = parser.pos
        skips = {}

        def advance():
            pos = parser.pos
            while pos in skips:
                _pos = skips[pos]
                parser.skip(_pos - pos)
                if pos == _pos:
                    break
                pos = _pos
            return pos

        all_opts = {}
        all_parts = []
        for i, parts in enumerate(self.all_parts):
            opts = 0
            for part in parts:
                if isinstance(part, Optional):
                    opts = (opts << 1) + 1
            opts += 1
            all_opts[i] = opts
            while opts > 0:
                opts -= 1
                opt = -1
                _parts = []
                for part in parts:
                    if isinstance(part, Optional):
                        opt += 1
                        if not opts & (1 << opt):
                            continue  # skip optional options
                    if isinstance(part, basestring):
                        part = Constant(part)
                    _parts.append(part)
                all_parts.append((i, opts, _parts))

        if self.ordered:
            permutations = [all_parts]
        else:
            permutations = list(itertools.permutations(all_parts))

        _args = []
        _kwargs = []
        _asvars = []
        _has_content = has_content

        for p, the_parts in enumerate(permutations):
            error = None
            skips.clear()
            found = [False] * len(the_parts)
            _args = []
            _kwargs = []
            _asvars = []
            _has_content = has_content
            for j, pieces in enumerate(the_parts):
                i, opts, parts = pieces
                if found[i]:
                    continue
                part_pos = advance()
                __args = []
                __kwargs = []
                __asvars = []
                __has_content = has_content
                try:
                    # print '\t' * level, '+++', '%s/%s (%s/%s opt)' % (p + 1, len(permutations), all_opts[i] - opts, all_opts[i]), repr(parser), '->', self._syntax(parts), 'pos:', pos
                    if parts:
                        for k, part in enumerate(parts):
                            last = (not self.multiple or j == len(the_parts) - 1) and k == len(parts) - 1
                            __args, __kwargs, __asvars, __has_content = part.parse(parser, __args, __kwargs, __asvars, __has_content, nxt if last else None, level + 1)
                    else:
                        if nxt and not parser.test(nxt):
                            parser.fail("expected token %r, got %r" % (nxt, parser.current))
                    found[i] = True
                    skips[part_pos] = parser.pos
                    _args.extend(__args)
                    _kwargs.extend(__kwargs)
                    _asvars.extend(__asvars)
                    _has_content = __has_content
                    # print '\t' * level, '\t', 'MATCH:', self._syntax(parts) if parts else '<empty>'
                except (JinjaTemplateSyntaxError, DjangoTemplateSyntaxError):
                    # print '\t' * level, '\t', 'TemplateSyntaxError:', e.message
                    if parser.pos != pos:
                        # print '\t' * level, '\t   >', repr(parser), 'rewind: %s (%s-%s)' % (parser.pos - pos, parser.pos, pos)
                        parser.rewind(parser.pos - pos)
                    continue

                if not self.multiple and any(found):
                    if nxt:
                        if parser.test(nxt):
                            break
                        else:
                            error = "expected token %r, got %r" % (nxt, parser.current)
                    else:
                        break

            part_pos = advance()

            if not error and nxt:
                if parser.test(nxt):
                    break
                else:
                    error = "expected token %r, got %r" % (nxt, parser.current)

            if not error:
                if self.optional or self.multiple and all(found) or not self.multiple and any(found):
                    break
                else:
                    error = "%s has the following syntax: {%% %s %%}" % (
                        self.name,
                        "%s %s" % (self.name, self.syntax()) if self.all_parts else "%s" % self.name
                    )

            parser.rewind(parser.pos - pos)

        args.extend(_args)
        kwargs.extend(_kwargs)
        asvars.extend(_asvars)
        has_content = _has_content

        if error:
            parser.fail(error)

        return args, kwargs, asvars, has_content


class Block(Blocks):
    parts = None
    optional = False
    multiple = False
    ordered = True

    def __init__(self, name, parts=None, **kwargs):
        if parts is None:
            self.parts = [Optional([Arguments()])]
        else:
            self.parts = parts
        kwargs['name'] = name
        super(Block, self).__init__(self.parts, **kwargs)


class Unordered(Blocks):
    optional = True
    multiple = True
    ordered = False


class Ordered(Blocks):
    optional = True
    multiple = True
    ordered = True


class Any(Blocks):
    optional = False
    multiple = False
    ordered = True


class Optional(Blocks):
    optional = True
    multiple = False
    ordered = True


class Parser(object):
    def test_any(self, *iterable):
        """Test against multiple token expressions."""
        for expr in iterable:
            if self.test(expr):
                return True
        return False

    def look(self, token):
        """Look at the next token."""
        self.next()
        result = self.test(token)
        self.rewind()
        return result

    def skip(self, n=1):
        """Got n tokens ahead."""
        for x in xrange(n):
            self.next()

    def next_if(self, expr):
        if self.test(expr):
            return self.next()

    def skip_if(self, expr):
        return self.next_if(expr) is not None


class BaseTagMixin(object):
    tag = None
    syntax = None
    blocks = None

    def parse_tag(self, parser):
        self.tag = tag = parser.next()

        bodies = []

        if isinstance(self.syntax, Blocks):
            self_syntax = [self.syntax]
        else:
            self_syntax = self.syntax

        blocks_optional = isinstance(self.blocks, Optional)
        if isinstance(self.blocks, Blocks):
            self_blocks = self.blocks.all_parts
        else:
            self_blocks = self.blocks

        blocks = {}
        block = Block(tag, self_syntax)
        block.args, block.kwargs, block.asvars, block.has_content = block.parse(parser, [], [], [], False, 'block_end')
        args, kwargs, asvars, has_content = block.args, block.kwargs, block.asvars, block.has_content
        last_block = main_block = block
        blocks['name:end%s' % tag] = main_block
        blocks['name:end_%s' % tag] = main_block

        macro_names = {}
        macro_name = tag

        if self_blocks is not None or blocks_optional and not has_content:
            if self_blocks:
                for block in self_blocks:
                    if block.name in blocks:
                        parser.fail("duplicated block %s!" % block.name)
                    blocks['name:%s' % block.name] = block

            while True:
                body = parser.new_Body(blocks.keys())
                token = parser.next()
                block = blocks['name:%s' % token]

                if macro_name == tag:
                    bodies.insert(0, (macro_name, body))
                else:
                    bodies.append((macro_name, body))
                    kwargs.append(parser.new_Pair(parser.new_Const(macro_name + '_args'), parser.new_List(last_block.args)))
                    kwargs.append(parser.new_Pair(parser.new_Const(macro_name + '_kwargs'), parser.new_Dict(last_block.kwargs)))

                if block == main_block:
                    while not parser.test('block_end'):
                        parser.next()
                else:
                    block.args, block.kwargs, block.asvars, block.has_content = block.parse(parser, [], [], [], False, 'block_end')
                    if block.asvars:
                        parser.fail("blocks cannot have assignments")

                macro_names.setdefault(block.name, 0)
                i = macro_names[block.name]
                macro_name = '%s_%s' % (block.name, i) if i else block.name
                macro_names[block.name] += 1
                if block.max_num and macro_names[block.name] > block.max_num:
                    parser.fail("can only define %s blocks of type %s" % (block.max_num, block.name))

                if block == main_block:
                    break

                last_block = block

            if self_blocks:
                for block in self_blocks:
                    macro_names.setdefault(block.name, 0)
                    macro_names[block.name]
                    if block.min_num and macro_names[block.name] < block.min_num:
                        parser.fail("you must define at least %s blocks of type %s" % (block.min_num, block.name))
        elif blocks_optional:
            args.insert(0, parser.new_Const(None))

        return bodies, args, kwargs, asvars
