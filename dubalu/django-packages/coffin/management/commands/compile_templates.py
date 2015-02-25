from __future__ import absolute_import

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clears out the search index completely."
    base_options = (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='If provided, no prompts will be issued to the user and the data will be wiped out.'),
    )
    option_list = BaseCommand.option_list + base_options

    def handle(self, **options):
        from ...common import env
        env.compile_templates(
            settings.JINJA2_COMPILED_TEMPLATES,
            extensions=set(['html', 'css', 'js', 'rml', 'txt']),
            zip=None,
        )
