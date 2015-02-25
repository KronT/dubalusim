#!/usr/bin/env python
import os
import sys
import warnings


def get_paths():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_NAME, __, PROJECT_SUFFIX = os.getenv('PROJECT', '').partition('.')
    if not PROJECT_NAME:
        try:
            PROJECT_FILE = os.path.join(BASE_DIR, 'PROJECT')
            PROJECT_NAME, __, PROJECT_SUFFIX = open(PROJECT_FILE, 'rt').read().strip().partition('.')
        except IOError:
            warnings.warn("No PROJECT_NAME assigned (missing '%s'?)")
            sys.exit(1)
    PROJECT_NAME = PROJECT_NAME.replace('-', '_')

    return [os.path.join(BASE_DIR, *p) for p in (
        ('dubalu',),
        ('projects',),
        ('dubalu', 'python-packages',),
        ('dubalu', 'django-packages',),
    )]


def setup():
    sys.path = get_paths() + sys.path

setup()

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dfw.settings")

    opts = [a for a in sys.argv if a[0] == '-']
    argv = [a for a in sys.argv if a[0] != '-']
    if len(argv) == 1:
        argv.append('runserver')
        argv.append('8000')
        if '--nostatic' not in opts:
            opts.append('--nostatic')
        if '--nothreading' not in opts:
            opts.append('--nothreading')
        # if '--noreload' not in opts:
        #     opts.append('--noreload')
        sys.argv = argv + opts
    elif len(argv) == 2 and argv[1].isdigit():
        argv.insert(1, 'runserver')
        if '--nostatic' not in opts:
            opts.append('--nostatic')
        if '--nothreading' not in opts:
            opts.append('--nothreading')
        # if '--noreload' not in opts:
        #     opts.append('--noreload')
        sys.argv = argv + opts

    # Settings and urls override:
    from django.conf import settings
    from dfw.middleware import get_project_settings
    project = settings.PROJECT
    try:
        regex, (project_name, project_suffix, project_settings) = get_project_settings()[project]
        settings.clear(project_settings)
        settings.PROJECT_NAME, settings.PROJECT_SUFFIX = project_name, project_suffix
        settings.PROJECT = project
        # from django.core import urlresolvers
        # from dfw.urls import get_urls
        # urlpatterns = get_urls(settings.PROJECT_NAME, settings.PROJECT_SUFFIX)
        # urlresolvers.set_urlconf(urlpatterns)
    except KeyError:
        pass

    from django.core.management import execute_from_command_line
    from ipdb import launch_ipdb_on_exception
    with launch_ipdb_on_exception():
        execute_from_command_line(sys.argv)
