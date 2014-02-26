# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
from rq import get_current_job

import itertools as it
from collections import Counter

import xlrd
from bob.data_table import DataTableColumn, DataTableMixin
from bob.menu import MenuItem, MenuHeader
from django.contrib import messages
from django.contrib.formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.core.urlresolvers import resolve, reverse
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.forms.models import modelformset_factory, formset_factory
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _

from ralph_assets.forms import (
    AddDeviceForm,
    AddPartForm,
    BasePartForm,
    BulkEditAssetForm,
    SplitDevice,
    DeviceForm,
    EditDeviceForm,
    BackOfficeEditDeviceForm,
    DataCenterEditDeviceForm,
    EditPartForm,
    MoveAssetPartForm,
    OfficeForm,
    SearchAssetForm,
    AssetColumnChoiceField,
    BackOfficeSearchAssetForm,
)
from ralph_assets.models import (
    Asset,
    AssetModel,
    AssetCategory,
    DeviceInfo,
    OfficeInfo,
    PartInfo,
)
from ralph_assets.models_assets import AssetType
from ralph_assets.models_history import AssetHistoryChange
from ralph.business.models import Venture
from ralph.ui.views.common import Base
from ralph.util.api_assets import get_device_components
from ralph.util.reports import Report, set_progress


SAVE_PRIORITY = 200
HISTORY_PAGE_SIZE = 25
MAX_PAGE_SIZE = 65535

QUOTATION_MARKS = re.compile(r"^\".+\"$")


class AssetsMixin(Base):
    template_name = "assets/base.html"

    def get_context_data(self, *args, **kwargs):
        ret = super(AssetsMixin, self).get_context_data(**kwargs)
        ret.update({
            'sidebar_items': self.get_sidebar_items(),
            'mainmenu_items': self.get_mainmenu_items(),
            'section': 'assets',
            'sidebar_selected': self.sidebar_selected,
            'section': self.mainmenu_selected,
        })

        return ret

    def get_mainmenu_items(self):
        mainmenu = [
            MenuItem(
                label='Data center',
                name='dc',
                fugue_icon='fugue-building',
                href='/assets/dc',
            ),
            MenuItem(
                label='BackOffice',
                fugue_icon='fugue-printer',
                name='back_office',
                href='/assets/back_office',
            ),
        ]
        if 'ralph_pricing' in settings.INSTALLED_APPS:
            mainmenu.append(
                MenuItem(
                    label='Ralph Pricing',
                    fugue_icon='fugue-money-coin',
                    name='back_office',
                    href='/pricing/all-ventures/',
                ),
            )
        return mainmenu

    def get_sidebar_items(self):
        return [
            MenuItem(
                label='XLS import',
                fugue_icon='fugue-document-excel',
                href=reverse('xls_upload'),
            ),
        ]


class DataCenterMixin(AssetsMixin):
    mainmenu_selected = 'dc'

    def get_sidebar_items(self):
        sidebar_menu = super(DataCenterMixin, self).get_sidebar_items()
        items = (
            ('/assets/dc/add/device', 'Add device', 'fugue-block--plus'),
            ('/assets/dc/add/part', 'Add part', 'fugue-block--plus'),
            ('/assets/dc/search', 'Search', 'fugue-magnifier'),
            ('/admin/ralph_assets', 'Admin', 'fugue-toolbox')
        )
        sidebar_menu = (
            [MenuHeader('Data center actions')] +
            [MenuItem(
             label=t[1],
             fugue_icon=t[2],
             href=t[0]
             ) for t in items]
        ) + sidebar_menu
        return sidebar_menu


class BackOfficeMixin(AssetsMixin):
    mainmenu_selected = 'back_office'

    def get_sidebar_items(self):
        sidebar_menu = super(BackOfficeMixin, self).get_sidebar_items()
        items = (
            ('/assets/back_office/add/device/', 'Add device',
                'fugue-block--plus'),
            ('/assets/back_office/add/part/', 'Add part',
                'fugue-block--plus'),
            ('/assets/back_office/search', 'Search', 'fugue-magnifier'),
        )
        sidebar_menu = (
            [MenuHeader('Back office actions')] +
            [MenuItem(
                label=t[1],
                fugue_icon=t[2],
                href=t[0]
            ) for t in items]
        ) + sidebar_menu
        return sidebar_menu


class DataTableColumnAssets(DataTableColumn):
    """
    A container object for all the information about a columns header

    :param foreign_field_name - set if field comes from foreign key
    """

    def __init__(self, header_name, foreign_field_name=None, **kwargs):
        super(DataTableColumnAssets, self).__init__(header_name, **kwargs)
        self.foreign_field_name = foreign_field_name


class AssetSearch(AssetsMixin, DataTableMixin):
    """The main-screen search form for all type of assets."""
    rows_per_page = 15
    csv_file_name = 'ralph.csv'
    sort_variable_name = 'sort'
    export_variable_name = 'export'
    _ = DataTableColumnAssets
    columns = [
        _('Dropdown', selectable=True, bob_tag=True),
        _('Type', bob_tag=True),
        _('SN', field='sn', sort_expression='sn', bob_tag=True, export=True),
        _('Barcode', field='barcode', sort_expression='barcode', bob_tag=True,
          export=True),
        _('Invoice date', field='invoice_date', sort_expression='model',
          bob_tag=True, export=True),
        _('Model', field='model', sort_expression='model', bob_tag=True,
          export=True),
        _('Invoice no.', field='invoice_no', sort_expression='invoice_no',
          bob_tag=True, export=True),
        _('Order no.', field='order_no', sort_expression='order_no',
          bob_tag=True, export=True),
        _('Status', field='status', sort_expression='status',
          bob_tag=True, export=True),
        _('Warehouse', field='warehouse', sort_expression='warehouse',
          bob_tag=True, export=True),
        _('Venture', field='venture', bob_tag=True, export=True),
        _('Department', field='department', foreign_field_name='venture',
          export=True),
        _('Price', field='price', sort_expression='price',
          bob_tag=True, export=True),
        _('Discovered', bob_tag=True, field='is_discovered', export=True,
            foreign_field_name='is_discovered'),
        _('Actions', bob_tag=True),
        _('Barcode salvaged', field='barcode_salvaged',
          foreign_field_name='part_info', export=True),
        _('Source device', field='source_device',
          foreign_field_name='part_info', export=True),
        _('Device', field='device',
          foreign_field_name='part_info', export=True),
        _('Provider', field='provider', export=True),
        _('Remarks', field='remarks', export=True),
        _('Source', field='source', export=True),
        _('Support peroid', field='support_peroid', export=True),
        _('Support type', field='support_type', export=True),
        _('Support void_reporting', field='support_void_reporting',
          export=True),
        _('Niw', field='niw', foreign_field_name='', export=True),
        _(
            'Ralph ID',
            field='device_info',
            foreign_field_name='ralph_device_id',
            export=True
        ),
        _('Type', field='type', export=True),
        _(
            'Deprecation rate',
            field='deprecation_rate',
            foreign_field_name='', export=True,
        ),
        #TODO: add task_link here?
    ]

    @property
    def search_fields(self):
        fields = [
            'niw',
            'category',
            'invoice_no',
            'model',
            'order_no',
            'part_info',
            'provider',
            'sn',
            'status',
            'deleted',
            'manufacturer',
            'barcode',
            'device_info',
            'source',
            'deprecation_rate',
            'unlinked',
            'ralph_device_id',
            'task_link',
        ]
        return fields


    def handle_search_data(self, get_csv=False):
        # handle simple 'equals' search fields at once.
        all_q = Q()
        for field in self.search_fields:
            field_value = self.request.GET.get(field)
            if field_value:
                exact = False
                # if search term is enclosed in "", we want exact matches
                if isinstance(field_value, basestring) and \
                        QUOTATION_MARKS.search(field_value):
                    exact = True
                    field_value = field_value[1:-1]
                if field == 'part_info':
                    if field_value == 'device':
                        all_q &= Q(part_info__isnull=True)
                    elif field_value == 'part':
                        all_q &= Q(part_info__gte=0)
                elif field == 'model':
                    if exact:
                        all_q &= Q(model__name=field_value)
                    else:
                        all_q &= Q(model__name__icontains=field_value)
                elif field == 'category':
                    part = self.get_search_category_part(field_value)
                    if part:
                        all_q &= part
                elif field == 'deleted':
                    if field_value.lower() == 'on':
                        all_q &= Q(deleted__in=(True, False))
                elif field == 'manufacturer':
                    if exact:
                        all_q &= Q(model__manufacturer__name=field_value)
                    else:
                        all_q &= Q(
                            model__manufacturer__name__icontains=field_value
                        )
                elif field == 'barcode':
                    if exact:
                        all_q &= Q(barcode=field_value)
                    else:
                        all_q &= Q(barcode__contains=field_value)
                elif field == 'sn':
                    if exact:
                        all_q &= Q(sn=field_value)
                    else:
                        all_q &= Q(sn__icontains=field_value)
                elif field == 'niw':
                    if exact:
                        all_q &= Q(niw=field_value)
                    else:
                        all_q &= Q(niw__icontains=field_value)
                elif field == 'provider':
                    if exact:
                        all_q &= Q(provider=field_value)
                    else:
                        all_q &= Q(provider__icontains=field_value)
                elif field == 'order_no':
                    if exact:
                        all_q &= Q(order_no=field_value)
                    else:
                        all_q &= Q(order_no__icontains=field_value)
                elif field == 'invoice_no':
                    if exact:
                        all_q &= Q(invoice_no=field_value)
                    else:
                        all_q &= Q(invoice_no__icontains=field_value)
                elif field == 'deprecation_rate':
                    deprecation_rate_query_map = {
                        'null': Q(deprecation_rate__isnull=True),
                        'deprecated': Q(deprecation_rate=0),
                        '6': Q(deprecation_rate__gt=0,
                               deprecation_rate__lte=6),
                        '12': Q(deprecation_rate__gt=6,
                                deprecation_rate__lte=12),
                        '24': Q(deprecation_rate__gt=12,
                                deprecation_rate__lte=24),
                        '48': Q(deprecation_rate__gt=24,
                                deprecation_rate__lte=48),
                        '48<': Q(deprecation_rate__gt=48),
                    }
                    all_q &= deprecation_rate_query_map[field_value]
                elif field == 'unlinked' and field_value.lower() == 'on':
                        all_q &= ~Q(device_info=None)
                        all_q &= Q(device_info__ralph_device_id=None)
                elif field == 'ralph_device_id':
                    if exact:
                        all_q &= Q(device_info__ralph_device_id=field_value)
                    else:
                        all_q &= Q(
                            device_info__ralph_device_id__icontains=field_value
                        )
                elif field == 'task_link':
                    if exact:
                        all_q &= Q(task_link=field_value)
                    else:
                        all_q &= Q(task_link__icontains=field_value)
                elif field == 'imei':
                    if exact:
                        all_q &= Q(office_info__imei=field_value)
                    else:
                        all_q &= Q(office_info__imei=field_value)
                else:
                    q = Q(**{field: field_value})
                    all_q = all_q & q
        # now fields within ranges.
        search_date_fields = [
            'invoice_date', 'request_date', 'delivery_date',
            'production_use_date', 'provider_order_date',
        ]
        for date in search_date_fields:
            start = self.request.GET.get(date + '_from')
            end = self.request.GET.get(date + '_to')
            if start:
                all_q &= Q(**{date + '__gte': start})
            if end:
                all_q &= Q(**{date + '__lte': end})
        if get_csv:
            return self.get_csv_data(self.get_all_items(all_q))
        else:
            self.data_table_query(self.get_all_items(all_q))

    def get_search_category_part(self, field_value):
        try:
            category_id = int(field_value)
        except ValueError:
            pass
        else:
            category = AssetCategory.objects.get(id=category_id)
            children = [x.id for x in category.get_children()]
            categories = [category_id, ] + children
            return Q(category_id__in=categories)

    def get_csv_header(self):
        header = super(AssetSearch, self).get_csv_header()
        return ['type'] + header

    def get_csv_rows(self, queryset, type, model):
        data = [self.get_csv_header()]
        total = queryset.count()
        processed = 0
        job = get_current_job()
        for asset in queryset:
            row = ['part', ] if asset.part_info else ['device', ]
            for item in self.columns:
                field = item.field
                if field:
                    nested_field_name = item.foreign_field_name
                    if nested_field_name == type:
                        cell = self.get_cell(
                            getattr(asset, type), field, model
                        )
                    elif nested_field_name == 'part_info':
                        cell = self.get_cell(asset.part_info, field, PartInfo)
                    elif nested_field_name == 'venture':
                        cell = self.get_cell(asset.venture, field, Venture)
                    elif nested_field_name == 'is_discovered':
                        cell = unicode(asset.is_discovered)
                    else:
                        cell = self.get_cell(asset, field, Asset)
                    row.append(unicode(cell))
            data.append(row)
            processed += 1
            set_progress(job, processed / total)
        set_progress(job, 1)
        return data

    def get_all_items(self, q_object):
        return Asset.objects.filter(q_object).order_by('id')

    def get_context_data(self, *args, **kwargs):
        ret = super(AssetSearch, self).get_context_data(*args, **kwargs)
        ret.update(
            super(AssetSearch, self).get_context_data_paginator(
                *args,
                **kwargs
            )
        )
        ret.update({
            'form': self.form,
            'header': self.header,
            'sort': self.sort,
            'columns': self.columns,
            'sort_variable_name': self.sort_variable_name,
            'export_variable_name': self.export_variable_name,
            'csv_url': self.request.path_info + '/csv',
        })
        return ret

    def get(self, *args, **kwargs):
        self.form = SearchAssetForm(
            self.request.GET, mode=_get_mode(self.request)
        )
        self.handle_search_data()
        if self.export_requested():
            return self.response
        return super(AssetSearch, self).get(*args, **kwargs)


class BackOfficeSearch(BackOfficeMixin, AssetSearch):
    header = 'Search BO Assets'
    sidebar_selected = 'search'
    template_name = 'assets/search_asset.html'
    _ = DataTableColumnAssets
    columns_nested = [
        _('Date of last inventory', field='date_of_last_inventory',
          foreign_field_name='office_info', export=True),
        _('Last logged user', field='last_logged_user',
          foreign_field_name='office_info', export=True),
        _('License key', field='license_key',
          foreign_field_name='office_info', export=True),
        _('License type', field='license_type',
          foreign_field_name='office_info', export=True),
        _('Unit price', field='unit_price',
          foreign_field_name='office_info', export=True),
        _('Version', field='version',
          foreign_field_name='office_info', export=True),
    ]

    def __init__(self, *args, **kwargs):
        self.columns = (
            self.columns + self.columns_nested
        )
        super(BackOfficeSearch, self).__init__(*args, **kwargs)

    def get_csv_data(self, queryset):
        data = super(BackOfficeSearch, self).get_csv_rows(
            queryset, type='office_info', model=OfficeInfo
        )
        return data

    def get_all_items(self, query):
        include_deleted = self.request.GET.get('deleted')
        if include_deleted and include_deleted.lower() == 'on':
            return Asset.admin_objects_bo.filter(query)
        return Asset.objects_bo.filter(query)

    def get(self, *args, **kwargs):
        self.form = BackOfficeSearchAssetForm(
            self.request.GET, mode=_get_mode(self.request)
        )
        self.handle_search_data()
        if self.export_requested():
            return self.response
        return super(AssetSearch, self).get(*args, **kwargs)

    @property
    def search_fields(self):
        search_fields = super(BackOfficeSearch, self).search_fields
        search_fields.append('imei')
        return search_fields

class DataCenterSearch(Report, DataCenterMixin, AssetSearch):
    header = 'Search DC Assets'
    sidebar_selected = 'search'
    template_name = 'assets/search_asset.html'
    _ = DataTableColumnAssets
    columns_nested = [
        _(
            'asset id',
            field='id',
            export=True,
        ),
        _(
            'Ralph device id',
            field='ralph_device_id',
            foreign_field_name='device_info',
            export=True,
        ), _(
            'Rack',
            field='rack',
            foreign_field_name='device_info',
            export=True,
        ),
        _(
            'U level',
            field='u_level',
            foreign_field_name='device_info',
            export=True,
        ),
        _(
            'U height',
            field='u_height',
            foreign_field_name='device_info',
            export=True,
        ),
        _(
            'modified',
            field='modified',
            export=True,
        ),
    ]

    def get_result(self, request, *args, **kwargs):
        self.form = SearchAssetForm(request.GET, mode=_get_mode(request))
        return self.handle_search_data(get_csv=True)

    def get_response(self, request, result):
        if self.export == 'csv':
            return self.make_csv_response(result)

    def __init__(self, *args, **kwargs):
        self.columns = (
            self.columns + self.columns_nested
        )
        super(DataCenterSearch, self).__init__(*args, **kwargs)

    def is_async(self, request, *args, **kwargs):
        self.export = request.GET.get('export')
        return self.export == 'csv'

    def get_csv_data(self, queryset):
        data = super(DataCenterSearch, self).get_csv_rows(
            queryset, type='device_info', model=DeviceInfo
        )
        return data

    def get_all_items(self, query):
        include_deleted = self.request.GET.get('deleted')
        if include_deleted and include_deleted.lower() == 'on':
            return Asset.admin_objects_dc.filter(query)
        return Asset.objects_dc.filter(query)


def _get_mode(request):
    current_url = resolve(request.get_full_path())
    url_name = current_url.url_name
    if url_name.startswith('dc'):
        url_name = 'dc'
    elif url_name.startswith('back_office'):
        url_name = 'back_office'
    return url_name


def _get_return_link(request):
    return "/assets/%s/" % _get_mode(request)


@transaction.commit_on_success
def _create_device(creator_profile, asset_data, device_info_data, sn, mode,
                   barcode=None):
    device_info = DeviceInfo()
    if mode == 'dc':
        device_info.ralph_device_id = device_info_data['ralph_device_id']
        device_info.u_level = device_info_data['u_level']
        device_info.u_height = device_info_data['u_height']
    device_info.save(user=creator_profile.user)
    asset = Asset(
        device_info=device_info,
        sn=sn.strip(),
        created_by=creator_profile,
        **asset_data
    )
    if barcode:
        asset.barcode = barcode
    asset.save(user=creator_profile.user)
    return asset.id


class AddDevice(Base):
    template_name = 'assets/add_device.html'

    def get_context_data(self, **kwargs):
        ret = super(AddDevice, self).get_context_data(**kwargs)
        ret.update({
            'asset_form': self.asset_form,
            'device_info_form': self.device_info_form,
            'form_id': 'add_device_asset_form',
            'edit_mode': False,
        })
        return ret

    def get(self, *args, **kwargs):
        mode = _get_mode(self.request)
        self.asset_form = AddDeviceForm(mode=mode)
        self.device_info_form = DeviceForm(
            mode=mode,
            exclude='create_stock',
        )
        return super(AddDevice, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        mode = _get_mode(self.request)
        self.asset_form = AddDeviceForm(self.request.POST, mode=mode)
        self.device_info_form = DeviceForm(
            self.request.POST,
            mode=mode,
            exclude='create_stock',
        )
        if self.asset_form.is_valid() and self.device_info_form.is_valid():
            creator_profile = self.request.user.get_profile()
            asset_data = {}
            for f_name, f_value in self.asset_form.cleaned_data.items():
                if f_name in ["barcode", "sn"]:
                    continue
                asset_data[f_name] = f_value
            serial_numbers = self.asset_form.cleaned_data['sn']
            barcodes = self.asset_form.cleaned_data['barcode']
            ids = []
            for sn, index in zip(serial_numbers, range(len(serial_numbers))):
                barcode = barcodes[index] if barcodes else None
                ids.append(
                    _create_device(
                        creator_profile,
                        asset_data,
                        self.device_info_form.cleaned_data,
                        sn,
                        mode,
                        barcode
                    )
                )
            messages.success(self.request, _("Assets saved."))
            cat = self.request.path.split('/')[2]
            if len(ids) == 1:
                return HttpResponseRedirect(
                    '/assets/%s/edit/device/%s/' % (cat, ids[0])
                )
            else:
                return HttpResponseRedirect(
                    '/assets/%s/bulkedit/?select=%s' % (
                        cat, '&select='.join(["%s" % id for id in ids]))
                )
        else:
            messages.error(self.request, _("Please correct the errors."))
        return super(AddDevice, self).get(*args, **kwargs)


class BackOfficeAddDevice(AddDevice, BackOfficeMixin):
    sidebar_selected = 'add device'


class DataCenterAddDevice(AddDevice, DataCenterMixin):
    sidebar_selected = 'add device'


@transaction.commit_on_success
def _create_part(creator_profile, asset_data, part_info_data, sn):
    part_info = PartInfo(**part_info_data)
    part_info.save(user=creator_profile.user)
    asset = Asset(
        part_info=part_info,
        sn=sn.strip(),
        created_by=creator_profile,
        **asset_data
    )
    asset.save(user=creator_profile.user)
    return asset.id


class AddPart(Base):
    template_name = 'assets/add_part.html'

    def get_context_data(self, **kwargs):
        ret = super(AddPart, self).get_context_data(**kwargs)
        ret.update({
            'asset_form': self.asset_form,
            'part_info_form': self.part_info_form,
            'form_id': 'add_part_form',
            'edit_mode': False,
        })
        return ret

    def initialize_vars(self):
        self.device_id = None

    def get(self, *args, **kwargs):
        self.initialize_vars()
        mode = _get_mode(self.request)
        self.asset_form = AddPartForm(mode=mode)
        self.device_id = self.request.GET.get('device')
        part_form_initial = {}
        if self.device_id:
            part_form_initial['device'] = self.device_id
        self.part_info_form = BasePartForm(
            initial=part_form_initial, mode=mode)
        return super(AddPart, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.initialize_vars()
        mode = _get_mode(self.request)
        self.asset_form = AddPartForm(self.request.POST, mode=mode)
        self.part_info_form = BasePartForm(self.request.POST, mode=mode)
        if self.asset_form.is_valid() and self.part_info_form.is_valid():
            creator_profile = self.request.user.get_profile()
            asset_data = self.asset_form.cleaned_data
            asset_data['barcode'] = None
            serial_numbers = self.asset_form.cleaned_data['sn']
            del asset_data['sn']
            ids = []
            for sn in serial_numbers:
                ids.append(
                    _create_part(
                        creator_profile, asset_data,
                        self.part_info_form.cleaned_data, sn
                    )
                )
            messages.success(self.request, _("Assets saved."))
            cat = self.request.path.split('/')[2]
            if len(ids) == 1:
                return HttpResponseRedirect(
                    '/assets/%s/edit/part/%s/' % (cat, ids[0])
                )
            else:
                return HttpResponseRedirect(
                    '/assets/%s/bulkedit/?select=%s' % (
                        cat, '&select='.join(["%s" % id for id in ids]))
                )
            return HttpResponseRedirect(_get_return_link(self.request))
        else:
            messages.error(self.request, _("Please correct the errors."))
        return super(AddPart, self).get(*args, **kwargs)


class BackOfficeAddPart(AddPart, BackOfficeMixin):
    sidebar_selected = 'add part'


class DataCenterAddPart(AddPart, DataCenterMixin):
    sidebar_selected = 'add part'


@transaction.commit_on_success
def _update_asset(modifier_profile, asset, asset_updated_data):
    if (
        'barcode' not in asset_updated_data or
        not asset_updated_data['barcode']
    ):
        asset_updated_data['barcode'] = None
    asset_updated_data.update({'modified_by': modifier_profile})
    asset.__dict__.update(**asset_updated_data)
    return asset


@transaction.commit_on_success
def _update_office_info(user, asset, office_info_data):
    if not asset.office_info:
        office_info = OfficeInfo()
    else:
        office_info = asset.office_info
    if office_info_data['attachment'] is None:
        del office_info_data['attachment']
    elif office_info_data['attachment'] is False:
        office_info_data['attachment'] = None
    office_info.__dict__.update(**office_info_data)
    office_info.save(user=user)
    asset.office_info = office_info
    return asset


@transaction.commit_on_success
def _update_device_info(user, asset, device_info_data):
    asset.device_info.__dict__.update(
        **device_info_data
    )
    asset.device_info.save(user=user)
    return asset


@transaction.commit_on_success
def _update_part_info(user, asset, part_info_data):
    if not asset.part_info:
        part_info = PartInfo()
    else:
        part_info = asset.part_info
    part_info.device = part_info_data.get('device')
    part_info.source_device = part_info_data.get('source_device')
    part_info.barcode_salvaged = part_info_data.get('barcode_salvaged')
    part_info.save(user=user)
    asset.part_info = part_info
    asset.part_info.save(user=user)
    return asset


class EditDevice(Base):
    template_name = 'assets/edit_device.html'

    def _get_form_by_mode(self, mode):
        EditDeviceForm = (
            BackOfficeEditDeviceForm if mode == 'back_office'
            else DataCenterEditDeviceForm
        )
        return EditDeviceForm

    def initialize_vars(self):
        self.parts = []
        self.office_info_form = None
        self.asset = None

    def get_context_data(self, **kwargs):
        ret = super(EditDevice, self).get_context_data(**kwargs)
        status_history = AssetHistoryChange.objects.all().filter(
            asset=kwargs.get('asset_id'), field_name__exact='status'
        ).order_by('-date')
        ret.update({
            'asset_form': self.asset_form,
            'device_info_form': self.device_info_form,
            'office_info_form': self.office_info_form,
            'part_form': MoveAssetPartForm(),
            'form_id': 'edit_device_asset_form',
            'edit_mode': True,
            'status_history': status_history,
            'parts': self.parts,
            'asset': self.asset,
            'history_link': self.get_history_link(),
        })
        return ret

    def get(self, *args, **kwargs):
        self.initialize_vars()
        self.asset = get_object_or_404(
            Asset.admin_objects,
            id=kwargs.get('asset_id')
        )
        if not self.asset.device_info:  # it isn't device asset
            raise Http404()
        mode = _get_mode(self.request)
        EditDeviceForm = self._get_form_by_mode(mode)
        self.asset_form = EditDeviceForm(instance=self.asset, mode=mode)
        if self.asset.type in AssetType.BO.choices:
            self.office_info_form = OfficeForm(instance=self.asset.office_info)
        self.device_info_form = DeviceForm(
            instance=self.asset.device_info,
            mode=mode,
        )
        self.parts = Asset.objects.filter(part_info__device=self.asset)
        return super(EditDevice, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.initialize_vars()
        post_data = self.request.POST
        self.asset = get_object_or_404(
            Asset.admin_objects,
            id=kwargs.get('asset_id')
        )
        mode = _get_mode(self.request)
        EditDeviceForm = self._get_form_by_mode(mode)
        self.asset_form = EditDeviceForm(
            post_data,
            instance=self.asset,
            mode=mode,
        )
        self.device_info_form = DeviceForm(
            post_data,
            mode=mode,
            instance=self.asset.device_info,
        )
        self.part_form = MoveAssetPartForm(post_data)
        if 'move_parts' in post_data.keys():
            destination_asset = post_data.get('new_asset')
            if not destination_asset or not Asset.objects.filter(
                id=destination_asset,
            ):
                messages.error(
                    self.request,
                    _("Source device asset does not exist"),
                )
            elif kwargs.get('asset_id') == destination_asset:
                messages.error(
                    self.request,
                    _("You can't move parts to the same device"),
                )
            else:
                for part_id in post_data.get('part_ids'):
                    info_part = PartInfo.objects.get(asset=part_id)
                    info_part.device_id = destination_asset
                    info_part.save()
                messages.success(self.request, _("Selected parts was moved."))
        elif 'asset' in post_data.keys():
            if self.asset.type in AssetType.BO.choices:
                self.office_info_form = OfficeForm(
                    post_data, self.request.FILES,
                )
            if all((
                self.asset_form.is_valid(),
                self.device_info_form.is_valid(),
                self.asset.type not in AssetType.BO.choices or
                self.office_info_form.is_valid()
            )):
                modifier_profile = self.request.user.get_profile()
                self.asset = _update_asset(
                    modifier_profile, self.asset, self.asset_form.cleaned_data
                )
                if self.asset.type in AssetType.BO.choices:
                    self.asset = _update_office_info(
                        modifier_profile.user, self.asset,
                        self.office_info_form.cleaned_data
                    )
                self.asset = _update_device_info(
                    modifier_profile.user, self.asset,
                    self.device_info_form.cleaned_data
                )
                if self.device_info_form.cleaned_data.get('create_stock'):
                    self.asset.create_stock_device()
                self.asset.save(user=self.request.user)
                messages.success(self.request, _("Assets edited."))
                cat = self.request.path.split('/')[2]
                return HttpResponseRedirect(
                    '/assets/%s/edit/device/%s/' % (cat, self.asset.id)
                )
            else:
                messages.error(self.request, _("Please correct the errors."))
                messages.error(
                    self.request, self.asset_form.non_field_errors(),
                )
        return super(EditDevice, self).get(*args, **kwargs)

    def get_history_link(self):
        mode = _get_mode(self.request)
        asset_id = self.asset.id
        if mode == 'dc':
            url = reverse('dc_device_history', args=[asset_id, ])
        elif mode == 'back_office':
            url = reverse('back_office_device_history', args=[asset_id, ])
        return url


class BackOfficeEditDevice(EditDevice, BackOfficeMixin):
    sidebar_selected = None


class DataCenterEditDevice(EditDevice, DataCenterMixin):
    sidebar_selected = None


class EditPart(Base):
    template_name = 'assets/edit_part.html'

    def get_context_data(self, **kwargs):
        ret = super(EditPart, self).get_context_data(**kwargs)
        status_history = AssetHistoryChange.objects.all().filter(
            asset=kwargs.get('asset_id'), field_name__exact='status'
        ).order_by('-date')
        ret.update({
            'asset_form': self.asset_form,
            'office_info_form': self.office_info_form,
            'part_info_form': self.part_info_form,
            'form_id': 'edit_part_form',
            'edit_mode': True,
            'status_history': status_history,
            'history_link': self.get_history_link(),
            'parent_link': self.get_parent_link(),
        })
        return ret

    def get(self, *args, **kwargs):
        self.asset = get_object_or_404(
            Asset.admin_objects,
            id=kwargs.get('asset_id')
        )
        if self.asset.device_info:  # it isn't part asset
            raise Http404()
        mode = _get_mode(self.request)
        self.asset_form = EditPartForm(instance=self.asset, mode=mode)
        self.office_info_form = OfficeForm(instance=self.asset.office_info)
        self.part_info_form = BasePartForm(
            instance=self.asset.part_info, mode=mode,
        )
        return super(EditPart, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.asset = get_object_or_404(
            Asset.admin_objects,
            id=kwargs.get('asset_id')
        )
        mode = _get_mode(self.request)
        self.asset_form = EditPartForm(
            self.request.POST,
            instance=self.asset,
            mode=mode
        )
        self.office_info_form = OfficeForm(
            self.request.POST, self.request.FILES)
        self.part_info_form = BasePartForm(self.request.POST, mode=mode)
        if all((
            self.asset_form.is_valid(),
            self.office_info_form.is_valid(),
            self.part_info_form.is_valid()
        )):
            modifier_profile = self.request.user.get_profile()
            self.asset = _update_asset(
                modifier_profile, self.asset,
                self.asset_form.cleaned_data
            )
            self.asset = _update_office_info(
                modifier_profile.user, self.asset,
                self.office_info_form.cleaned_data
            )
            self.asset = _update_part_info(
                modifier_profile.user, self.asset,
                self.part_info_form.cleaned_data
            )
            self.asset.save(user=self.request.user)
            messages.success(self.request, _("Part of asset was edited."))
            cat = self.request.path.split('/')[2]
            return HttpResponseRedirect(
                '/assets/%s/edit/part/%s/' % (cat, self.asset.id)
            )
        else:
            messages.error(self.request, _("Please correct the errors."))
            messages.error(self.request, self.asset_form.non_field_errors())
        return super(EditPart, self).get(*args, **kwargs)

    def get_parent_link(self):
        mode = _get_mode(self.request)
        asset = self.asset.part_info.source_device
        url = ''
        if asset:
            if mode == 'dc':
                url = reverse('dc_device_edit', args=[asset.id, ])
            elif mode == 'back_office':
                url = reverse('back_office_device_edit', args=[asset.id, ])
        return url

    def get_history_link(self):
        mode = _get_mode(self.request)
        asset_id = self.asset.id
        if mode == 'dc':
            url = reverse('dc_part_history', args=[asset_id, ])
        elif mode == 'back_office':
            url = reverse('back_office_part_history', args=[asset_id, ])
        return url


class BackOfficeEditPart(EditPart, BackOfficeMixin):
    sidebar_selected = None


class DataCenterEditPart(EditPart, DataCenterMixin):
    sidebar_selected = None


class HistoryAsset(BackOfficeMixin):
    template_name = 'assets/history_asset.html'
    sidebar_selected = None

    def get_context_data(self, **kwargs):
        query_variable_name = 'history_page'
        ret = super(HistoryAsset, self).get_context_data(**kwargs)
        asset_id = kwargs.get('asset_id')
        asset = Asset.admin_objects.get(id=asset_id)
        history = AssetHistoryChange.objects.filter(
            Q(asset_id=asset.id) |
            Q(device_info_id=getattr(asset.device_info, 'id', 0)) |
            Q(part_info_id=getattr(asset.part_info, 'id', 0)) |
            Q(office_info_id=getattr(asset.office_info, 'id', 0))
        ).order_by('-date')
        status = bool(self.request.GET.get('status', ''))
        if status:
            history = history.filter(field_name__exact='status')
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
            'status': status,
            'query_variable_name': query_variable_name,
            'asset': asset,
        })
        return ret


class BulkEdit(Base):
    template_name = 'assets/bulk_edit.html'

    def get_context_data(self, **kwargs):
        ret = super(BulkEdit, self).get_context_data(**kwargs)
        ret.update({
            'formset': self.asset_formset
        })
        return ret

    def get(self, *args, **kwargs):
        assets_count = Asset.objects.filter(
            pk__in=self.request.GET.getlist('select')).exists()
        if not assets_count:
            messages.warning(self.request, _("Nothing to edit."))
            return HttpResponseRedirect(_get_return_link(self.request))
        AssetFormSet = modelformset_factory(
            Asset,
            form=BulkEditAssetForm,
            extra=0
        )
        self.asset_formset = AssetFormSet(
            queryset=Asset.objects.filter(
                pk__in=self.request.GET.getlist('select')
            )
        )
        return super(BulkEdit, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        AssetFormSet = modelformset_factory(
            Asset,
            form=BulkEditAssetForm,
            extra=0
        )
        self.asset_formset = AssetFormSet(self.request.POST)
        if self.asset_formset.is_valid():
            with transaction.commit_on_success():
                instances = self.asset_formset.save(commit=False)
                for instance in instances:
                    instance.modified_by = self.request.user.get_profile()
                    instance.save(user=self.request.user)
            messages.success(self.request, _("Changes saved."))
            return HttpResponseRedirect(self.request.get_full_path())
        form_error = self.asset_formset.get_form_error()
        if form_error:
            messages.error(
                self.request,
                _("Please correct duplicated serial numbers or barcodes.")
            )
        else:
            messages.error(self.request, _("Please correct the errors."))
        return super(BulkEdit, self).get(*args, **kwargs)


class BackOfficeBulkEdit(BulkEdit, BackOfficeMixin):
    sidebar_selected = None

    def get_context_data(self, **kwargs):
        ret = super(BackOfficeBulkEdit, self).get_context_data(**kwargs)
        ret.update({
            'mode': 'BO',
        })
        return ret


class DataCenterBulkEdit(BulkEdit, DataCenterMixin):
    sidebar_selected = None

    def get_context_data(self, **kwargs):
        ret = super(DataCenterBulkEdit, self).get_context_data(**kwargs)
        ret.update({
            'mode': 'DC',
        })
        return ret


class DeleteAsset(AssetsMixin):

    def post(self, *args, **kwargs):
        record_id = self.request.POST.get('record_id')
        try:
            self.asset = Asset.objects.get(
                pk=record_id
            )
        except Asset.DoesNotExist:
            messages.error(
                self.request, _("Selected asset doesn't exists.")
            )
            return HttpResponseRedirect(_get_return_link(self.request))
        else:
            if self.asset.type < AssetType.BO:
                self.back_to = '/assets/dc/'
            else:
                self.back_to = '/assets/back_office/'
            if self.asset.has_parts():
                parts = self.asset.get_parts_info()
                messages.error(
                    self.request,
                    _("Cannot remove asset with parts assigned. Please remove "
                        "or unassign them from device first. ".format(
                            self.asset,
                            ", ".join([str(part.asset) for part in parts])
                        ))
                )
                return HttpResponseRedirect(
                    '{}{}{}'.format(
                        self.back_to, 'edit/device/', self.asset.id,
                    )
                )
            # changed from softdelete to real-delete, because of
            # key-constraints issues (sn/barcode) - to be resolved.
            self.asset.delete_with_info()
            return HttpResponseRedirect(self.back_to)


class DataCenterSplitDevice(DataCenterMixin):
    template_name = 'assets/split_edit.html'
    sidebar_selected = ''

    def get_context_data(self, **kwargs):
        ret = super(DataCenterSplitDevice, self).get_context_data(**kwargs)
        ret.update({
            'formset': self.asset_formset,
            'device': {
                'model': self.asset.model,
                'sn': self.asset.sn,
                'price': self.asset.price,
                'id': self.asset.id,
            },
        })
        return ret

    def get(self, *args, **kwargs):
        self.asset_id = self.kwargs.get('asset_id')
        self.asset = get_object_or_404(Asset, id=self.asset_id)
        if self.asset.has_parts():
            messages.error(self.request, _("This asset was splited."))
            return HttpResponseRedirect(
                reverse('dc_device_edit', args=[self.asset.id, ])
            )
        if self.asset.device_info.ralph_device_id:
            initial = self.get_proposed_components()
        else:
            initial = []
            messages.error(
                self.request,
                _(
                    'Asset not linked with ralph device, proposed components '
                    'not available'
                ),
            )
        extra = 0 if initial else 1
        AssetFormSet = formset_factory(form=SplitDevice, extra=extra)
        self.asset_formset = AssetFormSet(initial=initial)
        return super(DataCenterSplitDevice, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.asset_id = self.kwargs.get('asset_id')
        self.asset = Asset.objects.get(id=self.asset_id)
        AssetFormSet = formset_factory(
            form=SplitDevice,
            extra=0,
        )
        self.asset_formset = AssetFormSet(self.request.POST)
        if self.asset_formset.is_valid():
            with transaction.commit_on_success():
                for instance in self.asset_formset.forms:
                    form = instance.save(commit=False)
                    model_name = instance['model_user'].value()
                    form.model = self.create_asset_model(model_name)
                    form.type = AssetType.data_center
                    form.part_info = self.create_part_info()
                    form.modified_by = self.request.user.get_profile()
                    form.save(user=self.request.user)
            messages.success(self.request, _("Changes saved."))
            return HttpResponseRedirect(self.request.get_full_path())
        self.valid_duplicates('sn')
        self.valid_duplicates('barcode')
        self.valid_total_price()
        messages.error(self.request, _("Please correct the errors."))
        return super(DataCenterSplitDevice, self).get(*args, **kwargs)

    def valid_total_price(self):
        total_price = 0
        for instance in self.asset_formset.forms:
            total_price += float(instance['price'].value() or 0)
        valid_price = True if total_price == self.asset.price else False
        if not valid_price:
            messages.error(
                self.request,
                _(
                    "Total parts price must be equal to the asset price. "
                    "Total parts price (%s) != Asset "
                    "price (%s)" % (total_price, self.asset.price)
                )
            )
            return True

    def valid_duplicates(self, name):
        def get_duplicates(list):
            cnt = Counter(list)
            return [key for key in cnt.keys() if cnt[key] > 1]
        items = []
        for instance in self.asset_formset.forms:
            value = instance[name].value().strip()
            if value:
                items.append(value)
        duplicates_items = get_duplicates(items)
        for instance in self.asset_formset.forms:
            value = instance[name].value().strip()
            if value in duplicates_items:
                if name in instance.errors:
                    instance.errors[name].append(
                        'This %s is duplicated' % name
                    )
                else:
                    instance.errors[name] = ['This %s is duplicated' % name]
        if duplicates_items:
            messages.error(
                self.request,
                _("This %s is duplicated: (%s) " % (
                    name,
                    ', '.join(duplicates_items)
                )),
            )
            return True

    def create_asset_model(self, model_name):
        try:
            model = AssetModel.objects.get(name=model_name)
        except AssetModel.DoesNotExist:
            model = AssetModel()
            model.name = model_name
            model.save()
        return model

    def create_part_info(self):
        part_info = PartInfo()
        part_info.source_device = self.asset
        part_info.device = self.asset
        part_info.save(user=self.request.user)
        return part_info

    def get_proposed_components(self):
        try:
            components = list(get_device_components(
                ralph_device_id=self.asset.device_info.ralph_device_id
            ))
        except LookupError:
            components = []
        return components


class XlsUploadView(SessionWizardView):
    """The wizard view for xls upload."""
    template_name = 'assets/xls_upload_wizard.html'
    file_storage = FileSystemStorage(location=settings.FILE_UPLOAD_TEMP_DIR)

    def _process_xls(self, file_):
        book = xlrd.open_workbook(
            filename=file_.name,
            file_contents=file_.read(),
        )
        names_per_sheet = {}
        data_per_sheet = {}
        for sheet_name, sheet in book.items():
            if not sheet:
                continue
            names_per_sheet[sheet_name] = col_names = [
                cell.value for cell in sheet[0][1:]
            ]
            data_per_sheet[sheet_name] = {}
            for row in sheet[1:]:
                asset_id = int(row[0].value)
                data_per_sheet[sheet_name][asset_id] = {}
                for key, cell in it.izip(col_names, row[1:]):
                    data_per_sheet[sheet_name][asset_id][key] = cell.value
        return names_per_sheet, data_per_sheet

    def get_form(self, step=None, data=None, files=None):
        form = super(XlsUploadView, self).get_form(step, data, files)
        if step == 'column_choice':
            file_ = self.get_cleaned_data_for_step('upload')['file']
            names_per_sheet, data_per_sheet = self._process_xls(file_)
            self.storage.data['names_per_sheet'] = names_per_sheet
            self.storage.data['data_per_sheet'] = data_per_sheet
            for name_list in names_per_sheet.values():
                for name in name_list:
                    form.fields[name] = AssetColumnChoiceField(
                        label=name
                    )
        elif step == 'confirm':
            mappings = {}
            all_names = set(sum((
                list(name_list)
                for name_list in self.storage.data['names_per_sheet'].values()
            ), []))
            for k, v in self.get_cleaned_data_for_step(
                'column_choice'
            ).items():
                if k in all_names:
                    mappings[k] = v
            self.storage.data['mappings'] = mappings
        return form

    def get_context_data(self, form, **kwargs):
        data = super(XlsUploadView, self).get_context_data(form, **kwargs)
        if self.steps.current == 'confirm':
            mappings = self.storage.data['mappings']
            data_per_sheet = self.storage.data['data_per_sheet']
            all_columns = list(mappings.values())
            data_dicts = {}
            for sheet_name, sheet_data in data_per_sheet.items():
                for asset_id, asset_data in sheet_data.items():
                    data_dicts.setdefault(asset_id, {})
                    for key, value in asset_data.items():
                        data_dicts[asset_id][mappings[key]] = value
            table = []
            for asset_id, asset_data in data_dicts.items():
                row = [asset_id]
                for column in all_columns:
                    row.append(asset_data.get(column, ''))
                table.append(row)
            data['all_columns'] = all_columns
            data['table'] = table
        return data

    @transaction.commit_on_success
    def done(self, form_list):
        mappings = self.storage.data['mappings']
        data_per_sheet = self.storage.data['data_per_sheet']
        failed_assets = []
        for sheet_name, sheet_data in data_per_sheet.items():
            for asset_id, asset_data in sheet_data.items():
                try:
                    asset = Asset.objects.get(pk=asset_id)
                except Asset.DoesNotExist:
                    failed_assets.append(asset_id)
                    continue
                for key, value in asset_data.items():
                    setattr(asset, mappings[key], value)
                asset.save()
        ctx_data = self.get_context_data(None)
        ctx_data['failed_assets'] = failed_assets
        return render(
            self.request,
            'assets/xls_upload_wizard_done.html',
            ctx_data
        )
