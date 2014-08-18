# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import itertools as it
import urllib

from bob.data_table import DataTableColumn

from django.contrib import messages
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db.models import Sum, Count
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from ralph_assets.forms_sam import (
    SoftwareCategorySearchForm,
    LicenceSearchForm,
    AddLicenceForm,
    EditLicenceForm,
    BulkEditLicenceForm,
)
from ralph_assets.models_assets import MODE2ASSET_TYPE
from ralph_assets.models_history import LicenceHistoryChange
from ralph_assets.models_sam import (
    Licence,
    SoftwareCategory,
)
from ralph_assets.models_assets import ASSET_TYPE2MODE
from ralph_assets.views.asset import (
    Asset,
    HISTORY_PAGE_SIZE,
    MAX_PAGE_SIZE,
)
from ralph_assets.views.base import (
    AssetsBase,
    AjaxMixin,
    BulkEditBase,
    JsonResponseMixin,
    get_return_link,
)
from ralph_assets.views.search import GenericSearch


LICENCE_PAGE_SIZE = 10


class LicenseSelectedMixin(object):
    mainmenu_selected = 'licences'


class LicenceBaseView(LicenseSelectedMixin, AssetsBase):
    pass


class SoftwareCategoryNameColumn(DataTableColumn):
    """A column with software category name linking to the search of
    licences"""

    def render_cell_content(self, resource):
        name = super(
            SoftwareCategoryNameColumn, self
        ).render_cell_content(resource)
        return '<a href="/assets/sam/licences/?{qs}">{name}</a>'.format(
            qs=urllib.urlencode({'software_category': resource.id}),
            name=name,
        )


class LicenceLinkColumn(DataTableColumn):
    """A column that links to the edit page of a licence simply displaying
    'Licence' in a grid"""
    def render_cell_content(self, resource):
        return '<a href="{url}">{licence}</a>'.format(
            url=resource.url,
            licence=unicode(_('Licence')),
        )


class SoftwareCategoryList(LicenseSelectedMixin, GenericSearch):
    """Displays a list of software categories, which link to searches for
    licences."""

    Model = SoftwareCategory
    Form = SoftwareCategorySearchForm
    columns = [
        SoftwareCategoryNameColumn(
            'Name',
            bob_tag=True,
            field='name',
            sort_expression='name',
        ),
    ]


class CheckBoxColumn(DataTableColumn):
    """A column to select items in a grid"""
    def render_cell_content(self, resource):
        return '<input type="checkbox" name="select" value="{}">'.format(
            resource.id,
        )


class LicenceList(LicenseSelectedMixin, GenericSearch):
    """Displays a list of licences."""

    template_name = 'assets/licence_list.html'
    Model = Licence
    Form = LicenceSearchForm
    columns = [
        CheckBoxColumn(
            _('Dropdown'),
            selectable=True,
            bob_tag=True,
        ),
        LicenceLinkColumn(
            _('Type'),
            bob_tag=True,
        ),
        DataTableColumn(
            _('Inventory number'),
            bob_tag=True,
            field='niw',
            sort_expression='niw',
        ),
        DataTableColumn(
            _('Licence Type'),
            bob_tag=True,
            field='licence_type__name',
            sort_expression='licence_type__name',
        ),
        DataTableColumn(
            _('Manufacturer'),
            bob_tag=True,
            field='manufacturer__name',
            sort_expression='manufacturer__name',
        ),
        DataTableColumn(
            _('Software Category'),
            bob_tag=True,
            field='software_category',
            sort_expression='software_category__name',
        ),
        DataTableColumn(
            _('Property of'),
            bob_tag=True,
            field='property_of__name',
            sort_expression='property_of__name',
        ),
        DataTableColumn(
            _('Number of purchased items'),
            bob_tag=True,
            field='number_bought',
            sort_expression='number_bought',
        ),
        DataTableColumn(
            _('Used'),
            bob_tag=True,
            field='used',
        ),
        DataTableColumn(
            _('Invoice date'),
            bob_tag=True,
            field='invoice_date',
            sort_expression='invoice_date',
        ),
        DataTableColumn(
            _('Invoice no.'),
            bob_tag=True,
            field='invoice_no',
            sort_expression='invoice_no',
        ),
        DataTableColumn(
            _('Valid thru'),
            bob_tag=True,
            field='valid_thru',
            sort_expression='valid_thru',
        ),
    ]

    def get_context_data(self, **kwargs):
        context = super(LicenceList, self).get_context_data(**kwargs)
        context.update({'get_query': self.request.GET.urlencode()})
        return context


class LicenceFormView(LicenceBaseView):
    """Base view that displays licence form."""
    template_name = 'assets/add_licence.html'

    def _get_form(self, data=None, **kwargs):
        self.form = self.Form(
            mode=self.mode, data=data, **kwargs
        )

    def get_context_data(self, **kwargs):
        ret = super(LicenceFormView, self).get_context_data(**kwargs)
        ret.update({
            'form': self.form,
            'form_id': 'add_licence_form',
            'edit_mode': False,
            'caption': self.caption,
            'licence': getattr(self, 'licence', None),
            'mode': 'back_office',  # -1 to technical debt
        })
        return ret

    def _save(self, request, *args, **kwargs):
        try:
            licence = self.form.save(commit=False)
            if licence.asset_type is None:
                licence.asset_type = MODE2ASSET_TYPE[self.mode]
            licence.save()
            self.form.save_m2m()
            messages.success(self.request, self.message)
            return HttpResponseRedirect(licence.url)
        except ValueError:
            return super(LicenceFormView, self).get(request, *args, **kwargs)


class AddLicence(LicenceFormView):
    """Add a new licence"""

    caption = _('Add Licence')
    message = _('Licence added')
    Form = AddLicenceForm

    def get(self, request, *args, **kwargs):
        self._get_form()
        return super(AddLicence, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._get_form(request.POST)
        if self.form.is_valid():
            sns = self.form.cleaned_data['sn'] or it.repeat(None)
            for sn, niw in zip(sns, self.form.cleaned_data['niw']):
                self.form.instance.pk = None
                licence = self.form.save(commit=False)
                if licence.asset_type is None:
                    licence.asset_type = MODE2ASSET_TYPE[self.mode]
                licence.sn = sn
                licence.niw = niw
                licence.save()
            messages.success(self.request, '{} licences added'.format(len(
                self.form.cleaned_data['niw'],
            )))
            return HttpResponseRedirect(reverse('licence_list'))
        else:
            return super(AddLicence, self).get(request, *args, **kwargs)


class EditLicence(LicenceFormView):
    """Edit licence"""
    detect_changes = True
    caption = _('Edit Licence')
    message = _('Licence changed')
    Form = EditLicenceForm

    def get(self, request, licence_id, *args, **kwargs):
        self.licence = Licence.objects.get(pk=licence_id)
        self._get_form(instance=self.licence)
        return super(EditLicence, self).get(request, *args, **kwargs)

    def post(self, request, licence_id, *args, **kwargs):
        self.licence = Licence.objects.get(pk=licence_id)
        self._get_form(request.POST, instance=self.licence)
        return self._save(request, *args, **kwargs)


class LicenceBulkEdit(BulkEditBase, LicenceBaseView):
    model = Licence
    template_name = 'assets/bulk_edit.html'
    form_bulk = BulkEditLicenceForm


class DeleteLicence(AssetsBase):
    """Delete a licence."""

    def post(self, *args, **kwargs):
        record_id = self.request.POST.get('record_id')
        try:
            licence = Licence.objects.get(pk=record_id)
        except Asset.DoesNotExist:
            messages.error(self.request, _("Selected asset doesn't exists."))
            return HttpResponseRedirect(get_return_link(self.mode))
        self.back_to = reverse(
            'licence_list',
            kwargs={'mode': ASSET_TYPE2MODE[licence.asset_type]},
        )
        licence.delete()
        return HttpResponseRedirect(self.back_to)


class HistoryLicence(AssetsBase):
    template_name = 'assets/history.html'
    mainmenu_selected = 'licences'

    def get_context_data(self, **kwargs):
        query_variable_name = 'history_page'
        ret = super(HistoryLicence, self).get_context_data(**kwargs)
        licence_id = kwargs.get('licence_id')
        licence = Licence.objects.get(id=licence_id)
        history = LicenceHistoryChange.objects.filter(
            licence=licence,
        ).order_by('-date')
        try:
            page = int(self.request.GET.get(query_variable_name, 1))
        except ValueError:
            page = 1
        if page == 0:
            page = 1
            page_size = MAX_PAGE_SIZE
        else:
            page_size = HISTORY_PAGE_SIZE
        history_page = Paginator(history, page_size).page(page)
        ret.update({
            'history': history,
            'history_page': history_page,
            'show_status_button': False,
            'query_variable_name': query_variable_name,
            'object': licence,
            'object_url': licence.url,
            'title': _('History licence'),
        })
        return ret


class CountLicence(AjaxMixin, JsonResponseMixin, GenericSearch):
    mainmenu_selected = 'licences'  # required by AssetBase
    Model = Licence
    Form = LicenceSearchForm

    def get(self, request, *args, **kwargs):
        self.form = self.Form(request.GET)
        qs = self.handle_search_data(request)
        summary = qs.aggregate(total=Sum('number_bought'))
        summary.update(qs.annotate(assets_count=Count('assets')).aggregate(
            used_by_assets=Sum('assets_count'),
        ))
        summary.update(qs.annotate(users_count=Count('users')).aggregate(
            used_by_users=Sum('users_count'),
        ))
        return self.render_json_response(summary)
