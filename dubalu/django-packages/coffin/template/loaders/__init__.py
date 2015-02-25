from __future__ import absolute_import

import re

from django.conf import settings

from jinja2.loaders import FileSystemLoader, ChoiceLoader


match_loader = re.compile(r'^(django|coffin)\.')


def jinja_loader_from_django_loader(django_loader, args=None):
    """Attempts to make a conversion from the given Django loader to an
    similarly-behaving Jinja loader.

    :param django_loader: Django loader module string.
    :return: The similarly-behaving Jinja loader, or None if a similar loader
        could not be found.
    """
    if not match_loader.match(django_loader):
        return None
    for substr, func in _JINJA_LOADER_BY_DJANGO_SUBSTR.iteritems():
        if substr in django_loader:
            return func(*(args or []))
    return None


def _make_jinja_app_loader():
    """Makes an 'app loader' for Jinja which acts like
    :mod:`django.template.loaders.app_directories`.
    """
    from django.template.loaders.app_directories import app_template_dirs
    return FileSystemLoader(app_template_dirs)


def _make_jinja_filesystem_loader():
    """Makes a 'filesystem loader' for Jinja which acts like
    :mod:`django.template.loaders.filesystem`.
    """
    return FileSystemLoader(settings.TEMPLATE_DIRS)


def _make_jinja_cached_loader(*loaders):
    """Makes a loader for Jinja which acts like
    :mod:`django.template.loaders.cached`.
    """
    return ChoiceLoader(l for l in
        [jinja_loader_from_django_loader(l) for l in loaders] if l)


# Determine loaders from Django's conf.
_JINJA_LOADER_BY_DJANGO_SUBSTR = {  # {substr: callable, ...}
    'app_directories': _make_jinja_app_loader,
    'filesystem': _make_jinja_filesystem_loader,
    'cached': _make_jinja_cached_loader,
    'AppLoader': _make_jinja_app_loader,
    'FileSystemLoader': _make_jinja_filesystem_loader,
}
