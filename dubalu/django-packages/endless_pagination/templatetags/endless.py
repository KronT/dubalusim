"""Django Endless Pagination template tags."""

from __future__ import unicode_literals

from django import template
from django.utils.encoding import iri_to_uri

from endless_pagination import (
    models,
    settings,
    utils,
)
from endless_pagination.paginators import (
    DefaultPaginator,
    EmptyPage,
    InvalidPage,
    Page,
    LazyPaginator,
)

from templatetag_sugar.parser import Any, Optional, Variable, AssignmentVariable, Assignment


first_page = Optional([Variable('first_page'), ','])
per_page = Optional([first_page, Variable('per_page')])
page_number = Optional(['starting', 'from', 'page', Variable('page_number')])
querystring_key = Optional(['using', Variable('querystring_key')])
override_path = Optional(['with', Variable('override_path')])
paginate_syntax = Any(
    [per_page, AssignmentVariable('objects'), page_number, querystring_key, override_path, Assignment(asvar='endless')],
    [per_page, Variable('objects'), page_number, querystring_key, override_path, 'as', Assignment(), Assignment(asvar='endless')],
)

show_current_number_syntax = [page_number, querystring_key, Optional(['as', Assignment()])]


register = template.Library()


@register.inclusion_tag('endless/show_more.html', takes_context=True)
def show_more(context, label=None, loading=settings.LOADING):
    """Show the link to get the next page in a Twitter-like pagination.

    Usage::

        {% show_more %}

    Alternatively you can override the label passed to the default template::

        {% show_more "even more" %}

    You can override the loading text too::

        {% show_more "even more" "working" %}

    Must be called after ``{% paginate objects %}``.
    """
    # This template tag could raise a PaginationError: you have to call
    # *paginate* or *lazy_paginate* before including the showmore template.
    data = utils.get_data_from_context(context)
    page = data['page']
    # show the template only if there is a next page
    if page.has_next():
        request = context['request']
        page_number = page.next_page_number()
        # Generate the querystring.
        querystring_key = data['querystring_key']
        querystring = utils.get_querystring_for_page(
            request, page_number, querystring_key,
            default_number=data['default_number'])
        return {
            'label': label,
            'loading': loading,
            'path': iri_to_uri(data['override_path'] or request.path),
            'querystring': querystring,
            'querystring_key': querystring_key,
            'request': request,
        }
    # No next page, nothing to see.
    return {}


@register.assignment_tag(takes_context=True)
def get_pages(context):
    """Add to context the list of page links.

    Usage:

    .. code-block:: html+django

        {% get_pages %}

    This is mostly used for Digg-style pagination.
    This call inserts in the template context a *pages* variable, as a sequence
    of page links. You can use *pages* in different ways:

    - just print *pages* and you will get Digg-style pagination displayed:

    .. code-block:: html+django

        {{ pages }}

    - display pages count:

    .. code-block:: html+django

        {{ pages|length }}

    - check if the page list contains more than one page:

    .. code-block:: html+django

        {{ pages.paginated }}
        {# the following is equivalent #}
        {{ pages|length > 1 }}

    - get a specific page:

    .. code-block:: html+django

        {# the current selected page #}
        {{ pages.current }}

        {# the first page #}
        {{ pages.first }}

        {# the last page #}
        {{ pages.last }}

        {# the previous page (or nothing if you are on first page) #}
        {{ pages.previous }}

        {# the next page (or nothing if you are in last page) #}
        {{ pages.next }}

        {# the third page #}
        {{ pages.3 }}
        {# this means page.1 is the same as page.first #}

        {# the 1-based index of the first item on the current page #}
        {{ pages.current_start_index }}

        {# the 1-based index of the last item on the current page #}
        {{ pages.current_end_index }}

        {# the total number of objects, across all pages #}
        {{ pages.total_count }}

        {# the first page represented as an arrow #}
        {{ pages.first_as_arrow }}

        {# the last page represented as an arrow #}
        {{ pages.last_as_arrow }}

    - iterate over *pages* to get all pages:

    .. code-block:: html+django

        {% for page in pages %}
            {# display page link #}
            {{ page }}

            {# the page url (beginning with "?") #}
            {{ page.url }}

            {# the page path #}
            {{ page.path }}

            {# the page number #}
            {{ page.number }}

            {# a string representing the page (commonly the page number) #}
            {{ page.label }}

            {# check if the page is the current one #}
            {{ page.is_current }}

            {# check if the page is the first one #}
            {{ page.is_first }}

            {# check if the page is the last one #}
            {{ page.is_last }}
        {% endfor %}

    You can change the variable name, e.g.:

    .. code-block:: html+django

        {% get_pages as page_links %}

    Must be called after ``{% paginate objects %}``.
    """
    request = context['request']
    # This template tag could raise a PaginationError: you have to call
    # *paginate* or *lazy_paginate* before including the getpages template.
    data = utils.get_data_from_context(context)
    pages = models.PageList(
        request,
        data['page'],
        data['querystring_key'],
        default_number=data['default_number'],
        override_path=data['override_path'],
    )
    return pages


@register.simple_tag(takes_context=True)
def show_pages(context, page_obj):
    """Show page links.

    Usage:

    .. code-block:: html+django

        {% show_pages %}

    It is just a shortcut for:

    .. code-block:: html+django

        {% get_pages %}
        {{ pages }}

    You can set ``ENDLESS_PAGINATION_PAGE_LIST_CALLABLE`` in your *settings.py*
    to a callable, or to a dotted path representing a callable, used to
    customize the pages that are displayed.

    See the *__unicode__* method of ``endless_pagination.models.PageList`` for
    a detailed explanation of how the callable can be used.

    Must be called after ``{% paginate objects %}``.
    """
    return get_pages(context)


@register.advanced_tag(takes_context=True, syntax=paginate_syntax)
def paginate(context,
        first_page=None, per_page=None, objects=None, page_number=None,
        querystring_key=None, override_path=None,
        paginator_class=None):
    """Paginate objects.

    Usage:

    .. code-block:: html+django

        {% paginate entries %}

    After this call, the *entries* variable in the template context is replaced
    by only the entries of the current page.

    You can also keep your *entries* original variable (usually a queryset)
    and add to the context another name that refers to entries of the current
    page, e.g.:

    .. code-block:: html+django

        {% paginate entries as page_entries %}

    The *as* argument is also useful when a nested context variable is provided
    as queryset. In this case, and only in this case, the resulting variable
    name is mandatory, e.g.:

    .. code-block:: html+django

        {% paginate entries.all as entries %}

    The number of paginated entries is taken from settings, but you can
    override the default locally, e.g.:

    .. code-block:: html+django

        {% paginate 20 entries %}

    Of course you can mix it all:

    .. code-block:: html+django

        {% paginate 20 entries as paginated_entries %}

    By default, the first page is displayed the first time you load the page,
    but you can change this, e.g.:

    .. code-block:: html+django

        {% paginate entries starting from page 3 %}

    When changing the default page, it is also possible to reference the last
    page (or the second last page, and so on) by using negative indexes, e.g:

    .. code-block:: html+django

        {% paginate entries starting from page -1 %}

    This can be also achieved using a template variable that was passed to the
    context, e.g.:

    .. code-block:: html+django

        {% paginate entries starting from page page_number %}

    If the passed page number does not exist, the first page is displayed.

    If you have multiple paginations in the same page, you can change the
    querydict key for the single pagination, e.g.:

    .. code-block:: html+django

        {% paginate entries using article_page %}

    In this case *article_page* is intended to be a context variable, but you
    can hardcode the key using quotes, e.g.:

    .. code-block:: html+django

        {% paginate entries using 'articles_at_page' %}

    Again, you can mix it all (the order of arguments is important):

    .. code-block:: html+django

        {% paginate 20 entries
            starting from page 3 using page_key as paginated_entries %}

    Additionally you can pass a path to be used for the pagination:

    .. code-block:: html+django

        {% paginate 20 entries
            using page_key with pagination_url as paginated_entries %}

    This way you can easily create views acting as API endpoints, and point
    your Ajax calls to that API. In this case *pagination_url* is considered a
    context variable, but it is also possible to hardcode the URL, e.g.:

    .. code-block:: html+django

        {% paginate 20 entries with "/mypage/" %}

    If you want the first page to contain a different number of items than
    subsequent pages, you can separate the two values with a comma, e.g. if
    you want 3 items on the first page and 10 on other pages:

    .. code-block:: html+django

    {% paginate 3,10 entries %}

    You must use this tag before calling the {% show_more %} one.
    """
    request = context['request']

    if per_page is None:
        per_page = settings.PER_PAGE

    if first_page is None:
        first_page = per_page

    if page_number is None:
        default_number = 1
    else:
        default_number = page_number

    if querystring_key is None:
        querystring_key = settings.PAGE_LABEL

    if paginator_class is None:
        paginator_class = DefaultPaginator

    # Retrieve the queryset and create the paginator object.
    paginator = paginator_class(
        objects, per_page, first_page=first_page, orphans=settings.ORPHANS)

    # Normalize the default page number if a negative one is provided.
    if default_number < 0:
        default_number = utils.normalize_page_number(
            default_number, paginator.page_range)

    # The current request is used to get the requested page number.
    page_number = utils.get_page_number_from_request(
        request, querystring_key, default=default_number)

    # Get the page.
    try:
        try:
            page_obj = paginator.page(page_number)
        except EmptyPage:
            page_obj = paginator.page(1)
    except InvalidPage:
        page_obj = Page([], -1, paginator)

    # Populate the context with required data.
    data = {
        'default_number': default_number,
        'override_path': override_path,
        'page': page_obj,
        'querystring_key': querystring_key,
    }

    return page_obj, data


@register.advanced_tag(takes_context=True, syntax=paginate_syntax)
def lazy_paginate(context, **kwargs):
    """Lazy paginate objects.

    Paginate objects without hitting the database with a *select count* query.

    Use this the same way as *paginate* tag when you are not interested
    in the total number of pages.
    """
    kwargs['paginator_class'] = LazyPaginator
    return paginate(context, **kwargs)


@register.advanced_tag(takes_context=True, syntax=show_current_number_syntax)
def show_current_number(context, page_number=None, querystring_key=None):
    """Show the current page number, or insert it in the context.

    This tag can for example be useful to change the page title according to
    the current page number.

    To just show current page number:

    .. code-block:: html+django

        {% show_current_number %}

    If you use multiple paginations in the same page, you can get the page
    number for a specific pagination using the querystring key, e.g.:

    .. code-block:: html+django

        {% show_current_number using mykey %}

    The default page when no querystring is specified is 1. If you changed it
    in the `paginate`_ template tag, you have to call  ``show_current_number``
    according to your choice, e.g.:

    .. code-block:: html+django

        {% show_current_number starting from page 3 %}

    This can be also achieved using a template variable you passed to the
    context, e.g.:

    .. code-block:: html+django

        {% show_current_number starting from page page_number %}

    You can of course mix it all (the order of arguments is important):

    .. code-block:: html+django

        {% show_current_number starting from page 3 using mykey %}

    If you want to insert the current page number in the context, without
    actually displaying it in the template, use the *as* argument, i.e.:

    .. code-block:: html+django

        {% show_current_number as page_number %}
        {% show_current_number
            starting from page 3 using mykey as page_number %}

    """
    request = context['request']

    if page_number is None:
        page_number = 1

    if querystring_key is None:
        querystring_key = settings.PAGE_LABEL

    # The request object is used to retrieve the current page number.
    page_number = utils.get_page_number_from_request(
        request, querystring_key, default=page_number)

    return page_number
