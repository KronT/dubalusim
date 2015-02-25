from django.conf import settings
from django import template
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites import get_current_site

from templatetag_sugar.parser import Optional, Variable, Assignment

register = template.Library()


@register.advanced_tag(takes_context=True,
    syntax=[Optional([Variable('starts_with')]), Optional(['for', Variable('user')]), 'as', Assignment()])
def get_flatpages(context, starts_with=None, user=None, site_pk=None):
    """
    Context-function similar to get_flatpages tag in Django templates.

    Usage:
        <ul>
            {% for page in get_flatpages(starts_with='/about/', user=user, site_pk=site.pk) %}
                <li><a href="{{ page.url }}">{{ page.title }}</a></li>
            {% endfor %}
        </ul>

    """
    if 'request' in context:
        request = context['request']
        if hasattr(request, 'site'):
            site_pk = request.site.pk
        else:
            site_pk = get_current_site(request).pk
    else:
        site_pk = settings.SITE_ID

    flatpages = FlatPage.objects.filter(sites__id=site_pk or settings.SITE_ID)

    if starts_with:
        flatpages = flatpages.filter(url__startswith=starts_with)

    if not user or not user.is_authenticated():
        flatpages = flatpages.filter(registration_required=False)

    return flatpages
