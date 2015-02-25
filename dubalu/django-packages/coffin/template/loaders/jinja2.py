from __future__ import absolute_import

import re

from django.conf import settings
from django.template.loader import BaseLoader
from django.template import TemplateDoesNotExist

from ...common import env

from jinja2 import TemplateNotFound

match_loader = re.compile(r'^(django|coffin)\.')

_JINJA_EXCLUDE_APPS = (
    'admin',
    'admindocs',
)


class Loader(BaseLoader):
    is_usable = True

    def __init__(self):
        super(Loader, self).__init__()
        include_pattern = getattr(settings, 'JINGO_INCLUDE_PATTERN', None)
        if include_pattern:
            self.include_re = re.compile(include_pattern)
        else:
            self.include_re = None

    def load_template(self, template_name, template_dirs=None):
        # template_name = 'test_jinja2.html'
        if self.include_re:
            if not self.include_re.search(template_name):
                raise TemplateDoesNotExist(template_name)

        if hasattr(template_name, 'rsplit'):
            app = template_name.rsplit('/')[0]
            if app in getattr(settings, 'JINGO_EXCLUDE_APPS', _JINJA_EXCLUDE_APPS):
                raise TemplateDoesNotExist(template_name)
        try:
            template = env.get_template(template_name)
            return template, template.filename
        except TemplateNotFound:
            raise TemplateDoesNotExist(template_name)

    def load_template_source(self, template_name, template_dirs=None):
        try:
            source, filename, _ = env.loader.get_source(env, template_name)
        except TemplateNotFound:
            raise TemplateDoesNotExist(template_name)
        return source, filename
