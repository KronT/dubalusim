from dfw.sections.base import Section

from django.conf.urls import patterns, url, include


class LazyformsSection(Section):
    class Meta:
        urls = [
            patterns('',
                url(r'^lazyforms/', include('lazyforms.urls')),
            ),
        ]
