from __future__ import absolute_import

from django.conf import settings
from django.test import signals
import django.template

if not hasattr(django.template, '_coffin_patched'):

    # Monkey patch django
    django.template._coffin_patched = True

    from .template.library import Library

    django.template.base.Library = Library
    django.template.Library = Library

    if getattr(settings, 'JINJA2_ENABLED', False):

        from jinja2.environment import Template, new_context
        from .template.loader import find_template_source, get_template, get_template_from_string, render_to_string, select_template

        django.template.loader.find_template_source = find_template_source
        django.template.find_template_source = find_template_source

        django.template.loader.get_template = get_template
        django.template.get_template = get_template

        django.template.loader.get_template_from_string = get_template_from_string
        django.template.get_template_from_string = get_template_from_string

        django.template.loader.render_to_string = render_to_string
        django.template.render_to_string = render_to_string

        django.template.loader.select_template = select_template
        django.template.select_template = select_template

        if settings.TEMPLATE_DEBUG or settings.TEST:
            def Template__new_context(self, vars=None, shared=False, locals=None):
                signals.template_rendered.send(
                    sender=self,
                    template=self,
                    context=vars
                )
                return new_context(self.environment, self.name, self.blocks,
                                   vars, shared, self.globals, locals)
            Template.new_context = Template__new_context
