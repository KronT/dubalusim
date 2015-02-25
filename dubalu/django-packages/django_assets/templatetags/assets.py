import tokenize
import warnings

from django import template
from django_assets import Bundle
from django_assets.env import get_env
from webassets.exceptions import ImminentDeprecationWarning


def parse_debug_value(value):
    """Django templates do not know what a boolean is, and anyway we need to
    support the 'merge' option."""
    if isinstance(value, bool):
        return value
    try:
        from webassets.env import parse_debug_value
        return parse_debug_value(value)
    except ValueError:
        raise template.TemplateSyntaxError(
            '"debug" argument must be one of the strings '
            '"true", "false" or "merge", not "%s"' % value)


class AssetsNode(template.Node):

    # For testing, to inject a mock bundle
    BundleClass = Bundle

    def __init__(self, filters, output, debug, files, childnodes):
        self.childnodes = childnodes
        self.output = output
        self.files = files
        self.filters = filters
        self.debug = debug

    def resolve(self, context={}):
        """We allow variables to be used for all arguments; this function
        resolves all data against a given context;

        This is a separate method as the management command must have
        the ability to check if the tag can be resolved without a context.
        """
        def resolve_var(x):
            if x is None:
                return None
            else:
                try:
                    return template.Variable(x).resolve(context)
                except template.VariableDoesNotExist:
                    # Django seems to hide those; we don't want to expose
                    # them either, I guess.
                    raise
        def resolve_bundle(name):
            # If a bundle with that name exists, use it. Otherwise,
            # assume a filename is meant.
            try:
                return get_env()[name]
            except KeyError:
                return name

        return self.BundleClass(
            *[resolve_bundle(resolve_var(f)) for f in self.files],
            **{'output': resolve_var(self.output),
            'filters': resolve_var(self.filters),
            'debug': parse_debug_value(resolve_var(self.debug))})

    def render(self, context):
        bundle = self.resolve(context)

        result = u""
        for url in bundle.urls(env=get_env()):
            context.update({'ASSET_URL': url, 'EXTRA': bundle.extra})
            try:
                result += self.childnodes.render(context)
            finally:
                context.pop()
        return result


def assets(parser, token):
    filters = None
    output = None
    debug = None
    files = []

    # parse the arguments
    args = token.split_contents()[1:]
    for arg in args:
        # Handle separating comma; for backwards-compatibility
        # reasons, this is currently optional, but is enforced by
        # the Jinja extension already.
        if arg[-1] == ',':
            arg = arg[:-1]
            if not arg:
                continue

        # determine if keyword or positional argument
        arg = arg.split('=', 1)
        if len(arg) == 1:
            name = None
            value = arg[0]
        else:
            name, value = arg

        # handle known keyword arguments
        if name == 'output':
            output = value
        elif name == 'debug':
            debug = value
        elif name == 'filters':
            filters = value
        elif name == 'filter':
            filters = value
            warnings.warn('The "filter" option of the {% assets %} '
                          'template tag has been renamed to '
                          '"filters" for consistency reasons.',
                            ImminentDeprecationWarning)
        # positional arguments are source files
        elif name is None:
            files.append(value)
        else:
            raise template.TemplateSyntaxError('Unsupported keyword argument "%s"'%name)

    # capture until closing tag
    childnodes = parser.parse(("endassets",))
    parser.delete_first_token()
    return AssetsNode(filters, output, debug, files, childnodes)



# If Coffin is installed, expose the Jinja2 extension
try:
    from coffin.template import Library as CoffinLibrary
except ImportError:
    register = template.Library()
else:
    register = CoffinLibrary()
    from webassets.ext.jinja2 import AssetsExtension
    from django_assets.env import get_env
    register.tag(AssetsExtension, environment={'assets_environment': get_env()})

# expose the default Django tag
register.tag('assets', assets)


###

import zlib
import struct
from base64 import b64encode, b64decode

from django.contrib.staticfiles import finders

try:
    from PIL import Image
except ImportError:
    try:
        import Image
    except:
        Image = None


def png_chunk(type, data=b''):
    return (struct.pack('>i', len(data)) + type + data
            + struct.pack('>i', zlib.crc32(type + data)))


SIGN = b'\x89PNG\r\n\x1a\n'
IDAT = png_chunk(b'IDAT', zlib.compress(b''))
IEND = png_chunk(b'IEND')


def png(width, height):
    """
    Smallest possible transparent PNG generator.
    [http://garethrees.org/2007/11/14/pngcrush/]

    """
    png = SIGN + png_chunk(b'IHDR', struct.pack('>iibbbbb', width, height, 1, 0, 0, 0, 0)) + IDAT + IEND
    # print "%s\n" % len(png) + ''.join('%%%02x' % ord(a) for a in png).replace('%50%4e%47', 'PNG').replace('%49%48%44%52', 'IHDR').replace('%49%44%41%54', 'IDAT').replace('%49%45%4e%44', 'IEND')
    return png


def static_finder(glob):
    for finder in finders.get_finders():
        for path, storage in finder.list([], [glob]):
            yield path, storage


@register.simple_tag(name='image_url')
@register.simple_tag(name='static_url')
def url(src, *args, **kwargs):
    src = src.format(*args, **kwargs).replace('//', '/')
    try:
        ret = url._cache[src]
    except KeyError:
        bundle = Bundle(src, output=src, merge=False)
        urls = bundle.urls(env=get_env(), binary=True)
        ret = urls[0]
        url._cache[src] = ret
    return ret
url._cache = {}


@register.simple_tag
def img(*args, **kwargs):
    """
    Receives src, id, class, alt and builds an <img> element.

    """
    image = kwargs.pop('src', None)
    if not image:
        image, args = args[0], args[1:]
    css_id = kwargs.pop('id', '')
    css_class = kwargs.pop('class', '')
    alt = kwargs.pop('alt', '')
    lazy = kwargs.pop('lazy', False)
    image = image.format(*args, **kwargs).replace('//', '/')
    src = url(image)
    try:
        width, height, bg, _src = img._cache[image]
        if src != _src:
            raise KeyError
    except KeyError:
        try:
            path, storage = list(static_finder(image))[0]
        except IndexError:
            warnings.warn("Image not found: %s" % image)
            width, height, bg = '', '', ''
        else:
            if storage is not None:
                _file = storage.open(image)
            else:
                _file = image
            try:
                _image = Image.open(_file)
                _image.verify()
            except Exception:
                warnings.warn("Invalid image: %s" % image)
                width, height, bg = '', '', ''
            else:
                width, height = _image.size
                bg = "data:image/png;base64,%s" % b64encode(png(width, height))
        img._cache[image] = width, height, bg, src
    if lazy:
        template = '<img {css_id} src="{bg}" data-src="{src}" style="opacity:0" {css_class} {width} {height} {alt}>'
        css_class += ' lazy'
    else:
        template = '<img {css_id} src="{src}" {css_class} {width} {height} {alt}>'
    return template.format(
        src=src,
        bg=bg,
        alt='alt="%s"' % alt if alt else '',
        css_class='class="%s"' % css_class if css_class else '',
        css_id='id="%s"' % css_id if css_id else '',
        width='width="%d"' % width if width else '',
        height='height="%d"' % height if height else '',
    )
img._cache = {(0, 0): ''}


@register.simple_tag
def lazy_img(*args, **kwargs):
    return img(lazy=True, *args, **kwargs)


@register.simple_tag(takes_context=True)
def email_image_url(context, image=None, *args, **kwargs):
    base64 = kwargs.pop('base64', None)
    try:
        images = context['images']
    except KeyError:
        warnings.warn("email_image_url used, but no context variable named 'images' could be found!")
        return url(image) if image else ''

    if image:
        image = image.format(*args, **kwargs).replace('//', '/')
        try:
            path, storage = list(static_finder(image))[0]
        except IndexError:
            warnings.warn("Image not found: %s" % image)
            return ''
        data = storage.open(path).read()
    elif base64:
        data = b64decode(base64)

    img_id = 'img%d' % hash(data)
    images[img_id] = data
    return 'cid:%s' % img_id
