# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from datetime import timedelta, datetime

from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.timezone import template_localtime
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.encoding import force_text
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.urlresolvers import reverse
from django.contrib import messages

from endless_pagination.views import AjaxListView

from ..templatetags.common_views import resolve as resolveattr
from ..common.views import AjaxableResponseMixin, CreateMessageMixin, \
    UpdateMessageMixin


class BaseAdminTableMixin(AjaxableResponseMixin):
    base_template = 'common_views/bsadmintable/base.html'

    title = ""
    subtitle = ""

    def get_context_data(self, **kwargs):
        context = super(BaseAdminTableMixin, self).get_context_data(**kwargs)
        context.update(dict(
            title=self.get_title(),
            subtitle=self.get_subtitle(),
            base_template=self.base_template,
        ))

        return context

    def get_title(self):
        return self.title

    def get_subtitle(self):
        return self.subtitle


class HeadersBasedMixin(object):
    headers = None

    def get_headers(self):
        if self.headers is None:
            raise NotImplementedError
        return self.headers


class DeleteMessageMixin(object):
    success_message = ugettext("<strong>Success!</strong> The object was successfully deleted")

    def get_success_message(self):
        return self.success_message


class BaseAdminTableListView(HeadersBasedMixin, BaseAdminTableMixin, AjaxListView):
    context_object_name = 'item_list'
    template_name = 'common_views/bsadmintable/bs_admin_table_list.html'
    page_template = 'common_views/bsadmintable/bs_admin_table_list_page.html'
    add_button_live = False
    add_button_text = _('Add')

    detail_reverse = None
    edit_reverse = None
    add_reverse = None
    add_url = None

    def get_context_data(self, **kwargs):
        context = super(BaseAdminTableListView, self).get_context_data(**kwargs)

        if not self.can_view_items():
            raise PermissionDenied

        headers = self.get_headers()

        context.update({
            'headers': headers,
            'total_columns': len(headers),

            'add_button_text': self.get_add_button_text(),
            'add_button_live': self.add_button_live,

            'detail_reverse': self.detail_reverse,
            'edit_reverse': self.edit_reverse,
            'add_url': self.get_add_url(),

            'query': self.request.GET.get('search', ''),
            'dates_filter': self.dates_filter(),
            'filters': self.filters(),
            'over_search_widget': self.over_search_widget(),
            'below_search_widget': self.below_search_widget(),
            'location_tuples': self._get_location_tuples(),

            'can_create_items': self.can_create_items(),
        })

        return context

    def can_view_items(self):
        raise NotImplementedError("can_view_items hasn't been implemented")

    def can_create_items(self):
        raise NotImplementedError("can_create_items hasn't been implemented")

    def get_add_button_text(self):
        return self.add_button_text

    def get_add_button_src(self):
        return self.add_button_src

    def get_add_url(self):
        """
        Returns the supplied add URL.
        """
        if self.add_url:
            # Forcing possible reverse_lazy evaluation
            return force_text(self.add_url)
        elif self.add_reverse:
            return reverse(self.add_reverse)

    def over_search_widget(self):
        return ''

    def dates_filter(self):
        return ''

    def filters(self):
        return ''

    def below_search_widget(self):
        return ''

    def get_location_tuples(self):
        return [(0, '', self.title)]

    def _get_location_tuples(self):
        links = self.get_location_tuples()
        links.sort()

        for i in range(len(links)):
            if i < 2:
                links[i] = links[i][1:]
            else:
                links[i] = (links[i - 1][1] + "&" + links[i][1], links[i][2])
        return links


class BaseAdminTableDetailView(BaseAdminTableMixin, DetailView, CreateView):
    model = None
    template_name = 'common_views/bsadmintable/bs_admin_table_edit.html'
    helper = 'helper.detail'
    form_class = None

    def get_context_data(self, **kwargs):
        context = super(BaseAdminTableDetailView, self).get_context_data(**kwargs)

        self.object = context['object']

        if not self.can_view_item():
            raise PermissionDenied

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        context.update({
            'helper': self.helper,
            'form': form,
            'can_admin_item': self.can_admin_item(),
            'can_edit_item': self.can_edit_item(),
            'can_delete_item': self.can_delete_item(),
            'can_view_item': self.can_view_item(),
        })

        return context

    def can_admin_item(self):
        raise NotImplementedError("can_admin_item method hasn't been implemented")

    def can_edit_item(self):
        raise NotImplementedError("can_edit_item method hasn't been implemented")

    def can_view_item(self):
        raise NotImplementedError("can_view_item method hasn't been implemented")

    def can_delete_item(self):
        raise NotImplementedError("can_delete_item method hasn't been implemented")

    def render_to_response(self, context, **response_kwargs):
        if self.request.is_ajax():
            return self.render_to_json_response({
                'status': 'OK',
                'data': render_to_string(
                    self.get_template_names(),
                    context,
                    context_instance=RequestContext(self.request)
                ),
            })
        return super(BaseAdminTableDetailView, self).render_to_response(context, **response_kwargs)


class AdminTableCreateMixin(BaseAdminTableMixin):
    invalid_ajax_status = 200

    def get_context_data(self, **kwargs):
        context = super(AdminTableCreateMixin, self).get_context_data(**kwargs)
        context['helper'] = self.helper
        return context

    def get_form_valid_ajax_dictionary(self, form):
        return {
            'status': 'OK',
            'message': self.get_valid_message(),
            'settimer': True,
        }

    def get_form_invalid_ajax_dictionary(self, form):
        context = self.get_context_data(form=form)
        return {
            'status': 'ERR',
            'message': self.get_invalid_message(),
            'settimer': True,
            'data': render_to_string(
                self.get_template_names(),
                context,
                context_instance=RequestContext(self.request)
            ),
        }

    def can_create_items(self):
        raise NotImplementedError("can_create_items method hasn't been implemented")

    def can_edit_item(self):
        raise NotImplementedError("can_edit_item method hasn't been implemented")


class BaseAdminTableCreateView(CreateMessageMixin, AdminTableCreateMixin, CreateView):
    model = None
    template_name = 'common_views/bsadmintable/bs_admin_table_edit.html'
    helper = 'helper.layout'
    form_class = None
    success_url = None

    def get(self, request, *args, **kwargs):
        if not self.can_create_items():
            raise PermissionDenied

        if self.request.is_ajax():
            self.object = None
            form_class = self.get_form_class()
            form = self.get_form(form_class)
            context = self.get_context_data(form=form)
            return self.render_to_json_response({
                'status': 'OK',
                'data': render_to_string(
                    self.get_template_names(),
                    context,
                    context_instance=RequestContext(self.request)
                ),
            })
        return super(BaseAdminTableCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.can_create_items():
            raise PermissionDenied
        return super(BaseAdminTableCreateView, self).post(request, *args, **kwargs)

    def get_form_valid_ajax_dictionary(self, form):
        dictionary = super(BaseAdminTableCreateView, self).get_form_valid_ajax_dictionary(form)
        dictionary['reload'] = self.get_success_url()
        return dictionary


class BaseAdminTableUpdateView(HeadersBasedMixin, UpdateMessageMixin, AdminTableCreateMixin, UpdateView):
    model = None
    template_name = 'common_views/bsadmintable/bs_admin_table_edit.html'
    helper = 'helper.edit'
    form_class = None

    def get(self, request, *args, **kwargs):
        ret = super(BaseAdminTableUpdateView, self).get(request, *args, **kwargs)
        if not self.can_edit_item():
            raise PermissionDenied
        return ret

    def post(self, request, *args, **kwargs):
        ret = super(BaseAdminTableUpdateView, self).post(request, *args, **kwargs)
        if not self.can_edit_item():
            raise PermissionDenied
        return ret

    def get_form_valid_ajax_dictionary(self, form):
        dictionary = super(BaseAdminTableUpdateView, self).get_form_valid_ajax_dictionary(form)
        info = {}
        for i, k in enumerate(self.get_headers()):
            info['.item-%s' % i] = force_text(resolveattr({}, self.object, k[0], self))
        dictionary['info'] = info
        return dictionary

    def get_prefix(self):
        return getattr(self, 'prefix') or self.request.REQUEST.get('prefix', '')


class BaseAdminTableDeleteView(DeleteMessageMixin, BaseAdminTableMixin, DeleteView):
    http_method_names = ['post']
    model = None
    success_url = None
    undo_url = None

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not self.can_delete_item():
            raise PermissionDenied

        self.delete_object()

        if request.is_ajax():
            return self.render_to_json_response({
                'status': 'OK',
                'message': self.get_success_message(),
                'undo_url': self.get_undo_url(),
                'undo_message': ugettext("Undo"),
                'settimer': True,
            })
        else:
            messages.success(self.request, self.get_success_message())
        return HttpResponseRedirect(self.get_success_url())

    def delete_object(self):
        self.object.drop()

    def get_undo_url(self, object):
        """
        Returns the supplied undo URL.
        """
        if self.undo_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.undo_url)
        else:
            raise ImproperlyConfigured(
                "No URL to undo actions. Provide a undo_url.")
        return url

    def can_delete_item(self):
        raise NotImplementedError("can_delete_item hasn't been implemented")


class BaseAdminTableUndeleteView(DeleteMessageMixin, BaseAdminTableMixin, DeleteView):
    http_method_names = ['post']
    model = None
    success_url = None

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not self.can_delete_item():
            raise PermissionDenied

        self.undelete_object()

        if request.is_ajax():
            return self.render_to_json_response({
                'status': 'OK',
                'message': self.get_success_message(),
                'settimer': True,
            })
        else:
            messages.success(self.request, self.get_success_message())
        return HttpResponseRedirect(self.get_success_url())

    def undelete_object(self):
        if self.object.deleted_at is None:
            raise PermissionDenied  # FIXME: a more suitbale exception should be raised

        self.object.recover()

    def can_delete_item(self):
        raise NotImplementedError("can_delete_item hasn't been implemented")


class BaseAdminDateFilter(object):
    FILTER_LEGENDS = {
        'this_week': _("This week"),
        'this_month': _("This month"),
        'this_year': _("This year"),
        'previous_week': _("Previous week"),
        'previous_month': _("Previous month"),
        'previous_year': _("Previous year"),
    }

    def get_location_tuples(self):
        links = super(BaseAdminDateFilter, self).get_location_tuples()
        if 'date' in self.request.GET:
            date = self.request.GET['date'].strip()
            name = self.FILTER_LEGENDS.get(date)
            if date and name:
                links.append((1, 'date=' + date, name))
        if 'date-from' in self.request.GET:
            date = self.request.GET['date-from'].strip()
            name = date
            if date and name:
                links.append((1, 'date-from=' + date, name))
        if 'date-to' in self.request.GET:
            date = self.request.GET['date-to'].strip()
            name = date
            if date and name:
                links.append((1, 'date-to=' + date, name))
        return links

    def dates_filter(self):
        return render_to_string(
            'common_views/bsadmintable/_dates_filter.html',
            self.FILTER_LEGENDS,
        )

    def filter_date(self, today, date, query, fieldname="created_at"):
        if date is None:
            return query

        if isinstance(date, tuple):
            first_date = date[0] and template_localtime(datetime.strptime(date[0], '%Y-%m-%d'))
            last_date = date[1] and template_localtime(datetime.strptime(date[1], '%Y-%m-%d'))
            if first_date and last_date:
                if first_date > last_date:
                    first_date, last_date = last_date, first_date
                kwargs = {"%s__range" % fieldname: (first_date, last_date)}
            elif first_date:
                kwargs = {"%s__gte" % fieldname: first_date}
            elif last_date:
                kwargs = {"%s__lte" % fieldname: last_date}
            else:
                return query
            return query.filter(**kwargs)

        elif date.endswith('_week'):
            if date.startswith('previous_'):
                last_date = today - timedelta(days=today.weekday())
                first_date = last_date - timedelta(days=7)
            else:
                first_date = today - timedelta(days=today.weekday())
                last_date = today
            kwargs = {"%s__range" % fieldname: (first_date, last_date)}
            return query.filter(**kwargs)

        elif date.endswith('_month'):
            year = today.year
            month = today.month
            if date.startswith('previous_'):
                if month == 1:
                    month = 12
                    year -= 1
                else:
                    month -= 1
            kwargs = {
                "%s__year" % fieldname: year,
                "%s__month" % fieldname: month,
            }
            return query.filter(**kwargs)

        elif date.endswith('_year'):
            year = today.year
            month = today.month
            if date.startswith('previous_'):
                year -= 1
            kwargs = {
                "%s__year" % fieldname: year,
            }
            return query.filter(**kwargs)

        return query


class BaseAdminImportExportMixin(object):
    """
    To enable this menu, use a template that overloads the extra_filters block.
    If the default functionality suits your needs, just include the template:
    'common_views/bsadmintable/bs_admin_table_import_export_menu.html'.
    """
    @property
    def query(self):
        """Overload this property if the filters are activated, as this allows
        filtered exports. Example of query filtered by 'search' and 'date':

        @property
        def query(self):
            if not hasattr(self, '_query'):
                date = self.request.GET.get('date', '').encode('utf-8')
                search = self.request.GET.get('search', '').encode('utf-8')
                self._query = urllib.urlencode(dict(date=date, search=search))
            return self._query
        """
        return ''

    def get_export_all_link(self, *args, **kwargs):
        return '<a href="?action=export-all&%s"><i class="fa fa-save"></i> %s </a>' % (self.query, _("All"))

    def get_export_list_link(self, *args, **kwargs):
        return '<a href="?action=export-list&%s"><i class="fa fa-list"></i> %s </a>' % (self.query, _("Listed"))

    def get_template_link(self, *args, **kwargs):
        return '<a href="?action=template"><i class="fa fa-file-text"></i> %s </a>' % _("Download template")

    def get_import_url(self, *args, **kwargs):
        raise NotImplementedError

    def get_import_icon(self, *args, **kwargs):
        return 'fa-file-excel-o'

    def get_import_label(self, *args, **kwargs):
        return _("From CSV file")

    def get_import_link(self, *args, **kwargs):
        return '<a href="{0}"><i class="fa {1}"></i> {2} </a>'.format(
            self.get_import_url(),
            self.get_import_icon(),
            self.get_import_label(),
        )

    def get_context_data(self, **kwargs):
        context = super(BaseAdminImportExportMixin, self).get_context_data(**kwargs)
        context.update({
            'can_import_items': self.can_import_items(),
            'can_export_items': self.can_export_items(),
        })
        return context

    def get_csv(self, ignore_filters=False, empty=False):
        NotImplementedError

    def can_import_items(self):
        NotImplementedError

    def can_export_items(self):
        NotImplementedError
