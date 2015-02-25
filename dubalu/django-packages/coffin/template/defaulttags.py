from __future__ import absolute_import

import re
from datetime import datetime
try:
    from urllib.parse import urljoin
except ImportError:  # Python 2
    from urlparse import urljoin

from django.conf import settings
from django.utils import timezone
from django.utils import translation
from django.utils.encoding import smart_unicode, iri_to_uri
from django.template.defaultfilters import date

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.exceptions import TemplateSyntaxError
from jinja2 import Markup

from .library import Library


class LoadExtension(Extension):
    """The load-tag is a no-op in Coffin. Instead, all template libraries
    are always loaded.

    Note: Supporting a functioning load-tag in Jinja is tough, though
    theoretically possible. The trouble is activating new extensions while
    parsing is ongoing. The ``Parser.extensions`` dict of the current
    parser instance needs to be modified, but apparently the only way to
    get access would be by hacking the stack.
    """
    tags = set(['load'])

    def parse(self, parser):
        while not parser.stream.current.test('block_end'):
            next(parser.stream)
        return []


class AutoescapeExtension(Extension):
    """
    Template to output works in three phases in Jinja2: parsing,
    generation (compilation, AST-traversal), and rendering (execution).

    Unfortunatly, the environment ``autoescape`` option comes into effect
    during traversal, the part where we happen to have basically no control
    over as an extension. It determines whether output is wrapped in
    ``escape()`` calls.

    Solutions that could possibly work:

        * This extension could preprocess it's childnodes and wrap
          everything output related inside the appropriate
          ``Markup()`` or escape() call.

        * We could use the ``preprocess`` hook to insert the
          appropriate ``|safe`` and ``|escape`` filters on a
          string-basis. This is very unlikely to work well.

    There's also the issue of inheritance and just generally the nesting
    of autoescape-tags to consider.

    Other things of note:

        * We can access ``parser.environment``, but that would only
          affect the **parsing** of our child nodes.

        * In the commented-out code below we are trying to affect the
          autoescape setting during rendering. As noted, this could be
          necessary for rare border cases where custom extension use
          the autoescape attribute.

    Both the above things would break Environment thread-safety though!

    Overall, it's not looking to good for this extension.
    """

    tags = ['autoescape']

    def parse(self, parser):
        stream = parser.stream
        next(stream)

        while not parser.stream.current.test('block_end'):
            name = parser.stream.expect('name')
            if name.value == 'on':
                on_off = True
            elif name.value == 'off':
                on_off = False
        body = [
            nodes.Assign(nodes.Name('_autoescape', 'local'), nodes.EnvironmentAttribute('autoescape')),
            nodes.Assign(nodes.EnvironmentAttribute('autoescape'), nodes.Const(on_off)),
        ]
        body.extend(parser.parse_statements(('name:endautoescape',), drop_needle=True))
        body.append(nodes.Assign(nodes.EnvironmentAttribute('autoescape'), nodes.Name('_autoescape', 'local')))

        return body


class LocalizeExtension(Extension):
    tags = ['localize']

    def parse(self, parser):
        stream = parser.stream
        next(stream)

        while not parser.stream.current.test('block_end'):
            name = parser.stream.expect('name')
            if name.value == 'on':
                on_off = True
            elif name.value == 'off':
                on_off = False
        body = [
            nodes.Assign(nodes.Name('_localize', 'local'), nodes.EnvironmentAttribute('localize')),
            nodes.Assign(nodes.EnvironmentAttribute('localize'), nodes.Const(on_off)),
        ]
        body.extend(parser.parse_statements(('name:endlocalize',), drop_needle=True))
        body.append(nodes.Assign(nodes.EnvironmentAttribute('localize'), nodes.Name('_localize', 'local')))

        return body


class URLExtension(Extension):
    """Returns an absolute URL matching given view with its parameters.

    This is a way to define links that aren't tied to a particular URL
    configuration::

        {% url path.to.some_view arg1,arg2,name1=value1 %}

    Known differences to Django's url-Tag:

        - In Django, the view name may contain any non-space character.
          Since Jinja's lexer does not identify whitespace to us, only
          characters that make up valid identifers, plus dots and hyphens
          are allowed. Note that identifers in Jinja 2 may not contain
          non-ascii characters.

          As an alternative, you may specifify the view as a string,
          which bypasses all these restrictions. It further allows you
          to apply filters:

            {% url "меткаda.some-view"|afilter %}
    """

    tags = set(['url'])

    def parse(self, parser):
        stream = parser.stream

        tag = next(stream)

        # get view name
        if stream.current.test('string'):
            # Need to work around Jinja2 syntax here. Jinja by default acts
            # like Python and concats subsequent strings. In this case
            # though, we want {% url "app.views.post" "1" %} to be treated
            # as view + argument, while still supporting
            # {% url "app.views.post"|filter %}. Essentially, what we do is
            # rather than let ``parser.parse_primary()`` deal with a "string"
            # token, we do so ourselves, and let parse_expression() handle all
            # other cases.
            if stream.look().test('string'):
                token = next(stream)
                viewname = nodes.Const(token.value, lineno=token.lineno)
            else:
                viewname = parser.parse_expression()
        else:
            # parse valid tokens and manually build a string from them
            bits = []
            name_allowed = True
            while True:
                if stream.current.test_any('dot', 'sub', 'colon'):
                    bits.append(next(stream))
                    name_allowed = True
                elif stream.current.test('name') and name_allowed:
                    bits.append(next(stream))
                    name_allowed = False
                else:
                    break
            if not bits:
                raise TemplateSyntaxError("'%s' requires path to view" %
                    tag.value, tag.lineno)
            viewname = nodes.Name("".join([b.value for b in bits]), 'load')

        # get arguments
        args = []
        kwargs = []
        while not stream.current.test_any('block_end', 'name:as'):
            if args or kwargs:
                stream.skip_if('comma')
            if stream.current.test('name') and stream.look().test('assign'):
                key = nodes.Const(next(stream).value)
                next(stream)
                value = parser.parse_expression()
                kwargs.append(nodes.Pair(key, value, lineno=key.lineno))
            else:
                args.append(parser.parse_expression())

        def make_call_node(*kw):
            return self.call_method('_reverse', args=[
                viewname,
                nodes.List(args),
                nodes.Dict(kwargs),
                nodes.Name('_current_app', 'load'),
            ], kwargs=kw)

        # if an as-clause is specified, write the result to context...
        if stream.next_if('name:as'):
            var = nodes.Name(stream.expect('name').value, 'store')
            call_node = make_call_node(nodes.Keyword('fail',
                nodes.Const(False)))
            return nodes.Assign(var, call_node)
        # ...otherwise print it out.
        else:
            return nodes.Output([make_call_node()]).set_lineno(tag.lineno)

    @classmethod
    def _reverse(self, viewname, args, kwargs, current_app=None, fail=True):
        from django.core.urlresolvers import reverse, NoReverseMatch

        # Try to look up the URL twice: once given the view name,
        # and again relative to what we guess is the "main" app.
        url = ''
        urlconf = kwargs.pop('urlconf', None)
        try:
            url = reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs,
                current_app=current_app)
        except NoReverseMatch:
            projectname = settings.SETTINGS_MODULE.split('.')[0]
            try:
                url = reverse(projectname + '.' + viewname, urlconf=urlconf,
                              args=args, kwargs=kwargs)
            except NoReverseMatch:
                if fail:
                    raise
                else:
                    return ''

        return url


class WithExtension(Extension):
    """Adds a value to the context (inside this block) for caching and
    easy access, just like the Django-version does.

    For example::

        {% with person.some_sql_method as total %}
            {{ total }} object{{ total|pluralize }}
        {% endwith %}
    """
    tags = set(['with'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)
        node = nodes.Scope(lineno=tag.lineno)
        assignments = []
        while stream.current.type != 'block_end':
            lineno = stream.current.lineno
            if assignments:
                stream.skip_if('comma')

            if stream.current.test('name') and stream.look().test('assign'):
                target = parser.parse_assign_target()
                next(stream)
                expr = parser.parse_expression()
                assignments.append(nodes.Assign(target, expr, lineno=lineno))
                prev_arg = False
            elif stream.skip_if('name:as'):
                if prev_arg:
                    target = parser.parse_assign_target()
                    expr = prev_arg
                    assignments.append(nodes.Assign(target, expr, lineno=lineno))
                    prev_arg = False
                else:
                    parser.fail('no variable to set using', tag.lineno)
            else:
                prev_arg = parser.parse_expression()

        node.body = assignments + \
            list(parser.parse_statements(('name:endwith',),
                                         drop_needle=True))
        return node


class CacheExtension(Extension):
    """Exactly like Django's own tag, but supports full Jinja2
    expressiveness for all arguments.

        {% cache gettimeout()*2 "foo"+options.cachename  %}
            ...
        {% endcache %}

    This actually means that there is a considerable incompatibility
    to Django: In Django, the second argument is simply a name, but
    interpreted as a literal string. This tag, with Jinja2 stronger
    emphasis on consistent syntax, requires you to actually specify the
    quotes around the name to make it a string. Otherwise, allowing
    Jinja2 expressions would be very hard to impossible (one could use
    a lookahead to see if the name is followed by an operator, and
    evaluate it as an expression if so, or read it as a string if not.
    TODO: This may not be the right choice. Supporting expressions
    here is probably not very important, so compatibility should maybe
    prevail. Unfortunately, it is actually pretty hard to be compatibly
    in all cases, simply because Django's per-character parser will
    just eat everything until the next whitespace and consider it part
    of the fragment name, while we have to work token-based: ``x*2``
    would actually be considered ``"x*2"`` in Django, while Jinja2
    would give us three tokens: ``x``, ``*``, ``2``.

    General Syntax:

        {% cache [expire_time] [fragment_name] [var1] [var2] .. %}
            .. some expensive processing ..
        {% endcache %}

    Available by default (does not need to be loaded).

    Partly based on the ``FragmentCacheExtension`` from the Jinja2 docs.

    TODO: Should there be scoping issues with the internal dummy macro
    limited access to certain outer variables in some cases, there is a
    different way to write this. Generated code would look like this:

        internal_name = environment.extensions['..']._get_cache_value():
        if internal_name is not None:
            yield internal_name
        else:
            internal_name = ""  # or maybe use [] and append() for performance
            internalname += "..."
            internalname += "..."
            internalname += "..."
            environment.extensions['..']._set_cache_value(internalname):
            yield internalname

    In other words, instead of using a CallBlock which uses a local
    function and calls into python, we have to separate calls into
    python, but put the if-else logic itself into the compiled template.
    """

    tags = set(['cache'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno

        expire_time = parser.parse_expression()
        fragment_name = parser.parse_expression()
        vary_on = []
        while not parser.stream.current.test('block_end'):
            vary_on.append(parser.parse_expression())

        body = parser.parse_statements(['name:endcache'], drop_needle=True)

        return nodes.CallBlock(
            self.call_method('_cache_support',
                             [expire_time, fragment_name,
                              nodes.List(vary_on), nodes.Const(lineno)]),
            [], [], body).set_lineno(lineno)

    def _cache_support(self, expire_time, fragm_name, vary_on, lineno, caller):
        from django.core.cache import cache   # delay depending in settings
        from django.core.cache.utils import make_template_fragment_key

        try:
            expire_time = int(expire_time)
        except (ValueError, TypeError):
            raise TemplateSyntaxError('"%s" tag got a non-integer timeout value: %r' % (list(self.tags)[0], expire_time), lineno)
        cache_key = make_template_fragment_key(fragm_name, vary_on)
        value = cache.get(cache_key) if expire_time >= 0 else None
        if value is None:
            value = caller()
            if expire_time >= 0:
                cache.set(cache_key, value, expire_time)
        return value


class SpacelessExtension(Extension):
    """Removes whitespace between HTML tags, including tab and
    newline characters.

    Works exactly like Django's own tag.
    """

    tags = set(['spaceless'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(['name:endspaceless'], drop_needle=True)
        return nodes.CallBlock(
            self.call_method('_strip_spaces', [], [], None, None),
            [], [], body,
        ).set_lineno(lineno)

    def _strip_spaces(self, caller=None):
        from django.utils.html import strip_spaces_between_tags
        return strip_spaces_between_tags(caller().strip())


class CsrfTokenExtension(Extension):
    """Jinja2-version of the ``csrf_token`` tag.

    Adapted from a snippet by Jason Green:
    http://www.djangosnippets.org/snippets/1847/

    This tag is a bit stricter than the Django tag in that it doesn't
    simply ignore any invalid arguments passed in.
    """

    tags = set(['csrf_token'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        return nodes.Output([
            self.call_method('_render', [nodes.Name('csrf_token', 'load')]),
        ]).set_lineno(lineno)

    def _render(self, csrf_token):
        from django.template.defaulttags import CsrfTokenNode
        return Markup(CsrfTokenNode().render({'csrf_token': csrf_token}))


class IfsExtension(Extension):
    tags = set(['ifequal', 'ifnotequal'])
    _ops_map = {
        'ifequal': 'eq',
        'ifnotequal': 'ne',
    }

    def parse(self, parser):
        """Parse an if construct."""
        tag = next(parser.stream)
        node = result = nodes.If(lineno=tag.lineno)
        first = parser.parse_expression()
        second = parser.parse_expression()
        node.test = nodes.Compare(first, [nodes.Operand(self._ops_map[tag.value], second)])
        node.body = parser.parse_statements(('name:else', 'name:end' + tag.value))
        token = next(parser.stream)
        if token.test('name:else'):
            node.else_ = parser.parse_statements(('name:end' + tag.value,), drop_needle=True)
        else:
            node.else_ = []
        return result


class CommentExtension(Extension):
    tags = set(['comment'])

    def parse(self, parser):
        while True:
            token = next(parser.stream)
            if token.type == 'eof':
                parser.fail_eof(('name:endcomment',))
            if token.test('name:endcomment'):
                break
        return []


class FirstofExtension(Extension):
    tags = set(['firstof'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)

        args = []

        while not parser.stream.current.test_any('block_end'):
            if args:
                stream.skip_if('comma')
            args.append(parser.parse_expression())

        node = self.call_method('_firstof', args=[
            nodes.List(args),
        ])

        return nodes.Output([node]).set_lineno(tag.lineno)

    def _firstof(self, args):
        for value in args:
            if value:
                return smart_unicode(value)
        return u''


class NowExtension(Extension):
    tags = set(['now'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)

        format_string = parser.parse_expression()

        node = self.call_method('_now', args=[
            format_string,
        ])

        return nodes.Output([node]).set_lineno(tag.lineno)

    def _now(self, format_string):
        tzinfo = timezone.get_current_timezone() if settings.USE_TZ else None
        return date(datetime.now(tz=tzinfo), format_string)


class IfChangedExtension(Extension):
    tags = set(['ifchanged'])

    def parse(self, parser):
        """Parse an if construct."""
        stream = parser.stream
        tag = next(stream)
        lineno = tag.lineno

        args = []
        while not stream.current.test('block_end'):
            if args:
                stream.skip_if('comma')
            args.append(parser.parse_expression())
        args = nodes.Tuple(args, 'load', lineno=lineno)

        body = parser.parse_statements(('name:else', 'name:endifchanged'))
        _ifchanged_body = nodes.Macro(
            '_ifchanged_body',
            [], [], body).set_lineno(lineno)

        _ifchanged_else = None
        token = next(parser.stream)
        if token.test('name:else'):
            body = parser.parse_statements(('name:endifchanged',), drop_needle=True)
            _ifchanged_else = nodes.Macro(
                '_ifchanged_else',
                [], [], body).set_lineno(lineno)

        result = [_ifchanged_body]
        if _ifchanged_else:
            result += [_ifchanged_else]
        result += [
            nodes.Output([self.call_method('_ifchanged', args=[
                nodes.Name('loop', 'load'),
                nodes.Const(parser.free_identifier().name),
                args,
                nodes.Name('_ifchanged_body', 'load'),
                nodes.Name('_ifchanged_else', 'load') if _ifchanged_else else nodes.Const(None),
            ])])
        ]
        return result

    def _ifchanged(self, loop, key, args, caller_body, caller_else):
        _body = None
        if not args:
            _body = caller_body()
            args = (_body,)
        loop._last_seen = getattr(loop, '_last_seen', {})
        if loop._last_seen.get(key) != args:
            loop._last_seen[key] = args
            return _body if _body is not None else caller_body()
        elif caller_else:
            return caller_else()
        return ''


class CycleExtension(Extension):
    tags = set(['cycle'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)

        args = []

        while not parser.stream.current.test_any('block_end', 'name:as'):
            if stream.look().test('comma'):
                args.append(nodes.Const(next(stream).value))
                next(stream)
            elif stream.current.test('string'):
                args.append(nodes.Const(next(stream).value))
            else:
                args.append(parser.parse_expression())

        if parser.stream.current.test('name:as'):
            next(stream)
            asvar = nodes.Name(stream.expect('name').value, 'store')
        else:
            asvar = None

        node = self.call_method('_cycle', args=[
            nodes.Name('loop', 'load'),
            nodes.List(args),
        ])

        if asvar:
            return nodes.Assign(asvar, node)
        else:
            return nodes.Output([node]).set_lineno(tag.lineno)

    def _cycle(self, loop, args):
        return loop.cycle(*args)


class WidthRatioExtension(Extension):
    tags = set(['widthratio'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)

        value = parser.parse_expression()
        max_value = parser.parse_expression()
        if stream.current.test_any('integer', 'float'):
            max_width = nodes.Const(next(stream).value, lineno=tag.lineno)
        else:
            parser.fail("widthratio final argument must be an number")
        node = self.call_method('_widthratio', args=[
            value,
            max_value,
            max_width,
        ])
        return nodes.Output([node])

    def _widthratio(self, value, max_value, max_width):
        try:
            value = float(value)
            max_value = float(max_value)
            ratio = (value / max_value) * max_width
        except ZeroDivisionError:
            return '0'
        except ValueError:
            return ''
        return str(int(round(ratio)))


class GetAvailableLanguagesExtension(Extension):
    """
    This will store a list of available languages
    in the context.

    Usage::

        {% get_available_languages as languages %}
        {% for language in languages %}
        ...
        {% endfor %}

    This will just pull the LANGUAGES setting from
    your setting file (or the default settings) and
    put it into the named variable.
    """
    tags = set(['get_available_languages'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)

        stream.expect('name:as')
        asvar = nodes.Name(stream.expect('name').value, 'store')

        node = self.call_method('_get_available_languages', args=[
        ])
        return nodes.Assign(asvar, node).set_lineno(tag.lineno)

    def _get_available_languages(self):
        return [(k, translation.ugettext(v)) for k, v in settings.LANGUAGES]


class GetLanguageInfoExtension(Extension):
    """
    This will store the language information dictionary for the given language
    code in a context variable.

    Usage::

        {% get_language_info for LANGUAGE_CODE as l %}
        {{ l.code }}
        {{ l.name }}
        {{ l.name_local }}
        {{ l.bidi|yesno:"bi-directional,uni-directional" }}
    """
    tags = set(['get_language_info'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)

        stream.expect('name:for')
        lang_code = parser.parse_expression()

        stream.expect('name:as')
        asvar = nodes.Name(stream.expect('name').value, 'store')

        node = self.call_method('_get_language_info', args=[
            lang_code,
        ])
        return nodes.Assign(asvar, node).set_lineno(tag.lineno)

    def _get_language_info(self, lang_code):
        return translation.get_language_info(lang_code)


class GetLanguageInfoListExtension(Extension):
    """
    This will store a list of language information dictionaries for the given
    language codes in a context variable. The language codes can be specified
    either as a list of strings or a settings.LANGUAGES style tuple (or any
    sequence of sequences whose first items are language codes).

    Usage::

        {% get_language_info_list for LANGUAGES as langs %}
        {% for l in langs %}
          {{ l.code }}
          {{ l.name }}
          {{ l.name_local }}
          {{ l.bidi|yesno:"bi-directional,uni-directional" }}
        {% endfor %}
    """
    tags = set(['get_language_info_list'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)

        stream.expect('name:for')
        langs = parser.parse_expression()

        stream.expect('name:as')
        asvar = nodes.Name(stream.expect('name').value, 'store')

        node = self.call_method('_get_language_info_list', args=[
            langs,
        ])
        return nodes.Assign(asvar, node).set_lineno(tag.lineno)

    def _get_language_info(self, language):
        # ``language`` is either a language code string or a sequence
        # with the language code as its first item
        if len(language[0]) > 1:
            return translation.get_language_info(language[0])
        else:
            return translation.get_language_info(str(language))

    def _get_language_info_list(self, langs):
        return [self._get_language_info(lang) for lang in langs]


class GetCurrentLanguageExtension(Extension):
    """
    This will store the current language in the context.

    Usage::

        {% get_current_language as language %}

    This will fetch the currently active language and
    put it's value into the ``language`` context
    variable.
    """
    tags = set(['get_current_language'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)

        stream.expect('name:as')
        asvar = nodes.Name(stream.expect('name').value, 'store')

        node = self.call_method('_get_current_language', args=[
        ])
        return nodes.Assign(asvar, node).set_lineno(tag.lineno)

    def _get_current_language(self):
        return translation.get_language()


class GetCurrentLanguageBidiExtension(Extension):
    """
    This will store the current language layout in the context.

    Usage::

        {% get_current_language_bidi as bidi %}

    This will fetch the currently active language's layout and
    put it's value into the ``bidi`` context variable.
    True indicates right-to-left layout, otherwise left-to-right
    """
    tags = set(['get_current_language_bidi'])

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)

        stream.expect('name:as')
        asvar = nodes.Name(stream.expect('name').value, 'store')

        node = self.call_method('_get_current_language_bidi', args=[
        ])
        return nodes.Assign(asvar, node).set_lineno(tag.lineno)

    def _get_current_language_bidi(self):
        return translation.get_language_bidi()


class PrefixExtension(Extension):

    def parse(self, parser):
        stream = parser.stream
        lineno = stream.next().lineno

        call_node = self.call_method('render')

        if stream.next_if('name:as'):
            var = nodes.Name(stream.expect('name').value, 'store')
            return nodes.Assign(var, call_node).set_lineno(lineno)
        else:
            return nodes.Output([call_node]).set_lineno(lineno)

    def render(self, name):
        raise NotImplementedError()

    @classmethod
    def get_uri_setting(cls, name):
        try:
            from django.conf import settings
        except ImportError:
            prefix = ''
        else:
            prefix = iri_to_uri(getattr(settings, name, ''))
        return prefix


class GetStaticPrefixExtension(PrefixExtension):
    """
    Populates a template variable with the static prefix,
    ``settings.STATIC_URL``.

    Usage::

        {% get_static_prefix [as varname] %}

    Examples::

        {% get_static_prefix %}
        {% get_static_prefix as static_prefix %}

    """

    tags = set(['get_static_prefix'])

    def render(self):
        return self.get_uri_setting('STATIC_URL')


class GetMediaPrefixExtension(PrefixExtension):
    """
    Populates a template variable with the media prefix,
    ``settings.MEDIA_URL``.

    Usage::

        {% get_media_prefix [as varname] %}

    Examples::

        {% get_media_prefix %}
        {% get_media_prefix as media_prefix %}

    """

    tags = set(['get_media_prefix'])

    def render(self):
        return self.get_uri_setting('STATIC_URL')


class StaticExtension(PrefixExtension):
    """
    Joins the given path with the STATIC_URL setting.

    Usage::

        {% static path [as varname] %}

    Examples::

        {% static "myapp/css/base.css" %}
        {% static variable_with_path %}
        {% static "myapp/css/base.css" as admin_base_css %}
        {% static variable_with_path as varname %}

    """

    tags = set(['static'])

    def parse(self, parser):
        stream = parser.stream
        lineno = stream.next().lineno

        path = parser.parse_expression()
        call_node = self.call_method('get_statc_url', args=[path])

        if stream.next_if('name:as'):
            var = nodes.Name(stream.expect('name').value, 'store')
            return nodes.Assign(var, call_node).set_lineno(lineno)
        else:
            return nodes.Output([call_node]).set_lineno(lineno)

    @classmethod
    def get_statc_url(cls, path):
        return urljoin(PrefixExtension.get_uri_setting("STATIC_URL"), path)


class DjangoExtension(Extension):
    dj1tr = re.compile(r'(\{([%\{]).*?)\|slice:(([\'"])(\d*:\d*|\d+)\4)(.*?\2\})')

    dj2tr = (
        ('block.super', 'super()'),
        ('forloop.counter', 'loop.index'),
        ('forloop.counter0', 'loop.index0'),
        ('forloop.revcounter', 'loop.revindex'),
        ('forloop.revcounter0', 'loop.revindex0'),
        ('forloop.parentloop', 'loop'),  # FIXME: NOT SUPPORTED!
        ('forloop.', 'loop.'),
    )
    dj2tr_map = dict(dj2tr)
    dj2tr = re.compile(r'(\{([%{]).*?)' + '(' + '|'.join(re.escape(k) for k, v in dj2tr) + ')' + r'(.*?[%}]\})')

    def preprocess(self, source, name, filename=None):
        source = self.dj1tr.sub(r'\1[\5]\6', source)
        source = self.dj2tr.sub(lambda m: m.group(1) + self.dj2tr_map.get(m.group(3), m.group(3)) + m.group(4), source)
        return source


register = Library()
register.tag(LoadExtension)
register.tag(AutoescapeExtension)
register.tag(LocalizeExtension)
register.tag(URLExtension)
register.tag(WithExtension)
register.tag(CacheExtension)
register.tag(SpacelessExtension)
register.tag(CsrfTokenExtension)
register.tag(IfsExtension)
register.tag(CommentExtension)
register.tag(FirstofExtension)
register.tag(NowExtension)
register.tag(IfChangedExtension)
register.tag(CycleExtension)
register.tag(WidthRatioExtension)
register.tag(GetAvailableLanguagesExtension)
register.tag(GetLanguageInfoExtension)
register.tag(GetLanguageInfoListExtension)
register.tag(GetCurrentLanguageExtension)
register.tag(GetCurrentLanguageBidiExtension)
register.tag(GetStaticPrefixExtension)
register.tag(GetMediaPrefixExtension)
register.tag(StaticExtension)
register.tag(DjangoExtension)
