#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import time

from ajax_select.fields import (
    AutoCompleteSelectField,
    AutoCompleteField,
    AutoCompleteSelectMultipleField,
)
from bob.forms import (
    AJAX_UPDATE,
    CLONE,
    Dependency,
    DependencyForm,
    REQUIRE,
    SHOW,
)
from bob.forms import dependency_conditions
from collections import OrderedDict
from django.core.urlresolvers import reverse
from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    DateField,
    Form,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    ValidationError,
)
from django.forms.widgets import HiddenInput, Textarea
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from mptt.forms import TreeNodeChoiceField
from ralph_assets.models import (
    Asset,
    AssetCategory,
    AssetCategoryType,
    AssetSource,
    AssetStatus,
    AssetType,
    DeviceInfo,
    OfficeInfo,
    PartInfo,
    Service,
)
from ralph_assets import models_assets
from ralph.ui.widgets import DateWidget, ReadOnlyWidget


RALPH_DATE_FORMAT = ['%Y-%m-%d']

asset_fieldset = lambda: OrderedDict([
    ('Basic Info', [
        'type', 'category', 'model', 'niw', 'barcode', 'sn', 'warehouse',
        'location', 'status', 'task_url', 'loan_end_date', 'remarks',
        'service_name',
    ]),
    ('Financial Info', [
        'order_no', 'invoice_date', 'invoice_no', 'price', 'provider',
        'deprecation_rate', 'source', 'request_date', 'provider_order_date',
        'delivery_date',
    ]),
    ('User Info', [
        'user', 'owner', 'employee_id', 'company', 'department', 'manager',
        'profit_center', 'cost_center',
    ]),
])

LOOKUPS = {
    'asset': ('ralph_assets.models', 'DeviceLookup'),
    'asset_model': ('ralph_assets.models', 'AssetModelLookup'),
    'asset_dcmodel': ('ralph_assets.models', 'DCAssetModelLookup'),
    'asset_bomodel': ('ralph_assets.models', 'BOAssetModelLookup'),
    'asset_dcdevice': ('ralph_assets.models', 'DCDeviceLookup'),
    'asset_bodevice': ('ralph_assets.models', 'BODeviceLookup'),
    'asset_warehouse': ('ralph_assets.models', 'WarehouseLookup'),
    'asset_user': ('ralph_assets.models', 'UserLookup'),
    'asset_manufacturer': ('ralph_assets.models', 'AssetManufacturerLookup'),
    'free_licences': ('ralph_assets.models', 'FreeLicenceLookup'),
    'ralph_device': ('ralph_assets.models', 'RalphDeviceLookup'),

}


def move_after(_list, static, dynamic):
    """
    Move *static* elem. after *dynamic* elem. in list *_list*
    Both *static* and *dynamic* MUST belong to *_list*.
    :return list: return _list with moved *dynamic* elem.
    """
    _list.remove(dynamic)
    next_pos = _list.index(static) + 1
    _list.insert(next_pos, dynamic)
    return _list

imei_until_2003 = re.compile(r'^\d{6} *\d{2} *\d{6} *\d$')
imei_since_2003 = re.compile(r'^\d{8} *\d{6} *\d$')


def validate_imei(imei):
    is_imei = imei_until_2003.match(imei) or imei_since_2003.match(imei)
    if not is_imei:
        raise ValidationError('"{}" is not IMEI format'.format(imei))


class ModeNotSetException(Exception):
    pass


class BarcodeField(CharField):
    def to_python(self, value):
        return value if value else None


class BulkEditAssetForm(ModelForm):
    '''
        Form model for bulkedit assets, contains column definition and
        validadtion. Most important are sn and barcode fields. When you type
        sn you can place many sn numbers separated by pressing enter.
        Barcode count must be the same like sn count.
    '''
    class Meta:
        model = Asset
        fields = (
            'type', 'model', 'warehouse', 'property_of', 'device_info',
            'invoice_no', 'invoice_date', 'order_no', 'sn', 'barcode', 'price',
            'deprecation_rate', 'support_price', 'support_period',
            'support_type', 'support_void_reporting', 'provider', 'source',
            'status', 'task_url', 'request_date', 'delivery_date',
            'production_use_date', 'provider_order_date', 'production_year',
            'user', 'owner', 'service_name',
        )
        widgets = {
            'request_date': DateWidget(),
            'delivery_date': DateWidget(),
            'invoice_date': DateWidget(),
            'production_use_date': DateWidget(),
            'provider_order_date': DateWidget(),
            'device_info': HiddenInput(),
        }

    barcode = BarcodeField(max_length=200, required=False)
    source = ChoiceField(
        required=False,
        choices=[('', '----')] + AssetSource(),
    )
    model = AutoCompleteSelectField(
        LOOKUPS['asset_model'],
        required=True,
        plugin_options=dict(
            add_link='/admin/ralph_assets/assetmodel/add/?name=',
        )
    )
    owner = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=False,
    )
    user = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=False,
    )

    def clean(self):
        invoice_no = self.cleaned_data.get('invoice_no', False)
        invoice_date = self.cleaned_data.get('invoice_date', False)
        if 'invoice_date' not in self.errors:
            if invoice_no and not invoice_date:
                self._errors["invoice_date"] = self.error_class([
                    _("Invoice date cannot be empty.")
                ])
        if 'invoice_on' not in self.errors:
            if invoice_date and not invoice_no:
                self._errors["invoice_no"] = self.error_class([
                    _("Invoice number cannot be empty.")
                ])
        serial_number_unique = _check_serial_numbers_uniqueness(
            [self.cleaned_data['sn']]
        )[0]
        if 'sn' in self.changed_data and not serial_number_unique:
            self._errors["sn"] = self.error_class([
                _("Asset with this Sn already exists.")
            ])
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(BulkEditAssetForm, self).__init__(*args, **kwargs)
        fillable_fields = [
            'type', 'model', 'device_info', 'invoice_no', 'order_no',
            'request_date', 'delivery_date', 'invoice_date',
            'production_use_date', 'provider_order_date',
            'provider_order_date', 'support_period', 'support_type',
            'provider', 'source', 'status', 'production_year', 'purpose',
            'property_of', 'service_name',
        ]
        for field_name in self.fields:
            if field_name in fillable_fields:
                classes = "span12 fillable"
            elif field_name == 'support_void_reporting':
                classes = ""
            else:
                classes = "span12"
            self.fields[field_name].widget.attrs = {'class': classes}
        group_type = AssetType.from_id(self.instance.type).group.name
        if group_type == 'DC':
            self.fields['type'].choices = [
                (c.id, c.desc) for c in AssetType.DC.choices]

            self.fields['model'].widget.channel = LOOKUPS['asset_dcmodel']
            del self.fields['type']
        elif group_type == 'BO':
            self.fields['model'].widget.channel = LOOKUPS['asset_bomodel']
            self.fields['type'].choices = [('', '---------')] + [
                (choice.id, choice.name) for choice in AssetType.BO.choices
            ]

            self.fields['type'].choices = [
                (c.id, c.desc) for c in AssetType.BO.choices]


class BackOfficeBulkEditAssetForm(BulkEditAssetForm):

    purpose = ChoiceField(
        choices=[('', '----')] + models_assets.AssetPurpose(),
        label='Purpose',
        required=False,
    )


class DataCenterBulkEditAssetForm(BulkEditAssetForm):
    pass


class DeviceForm(ModelForm):
    class Meta:
        model = DeviceInfo
        fields = (
            'u_level',
            'u_height',
            'ralph_device_id',
        )
    force_unlink = BooleanField(required=False, label="Force unlink")
    create_stock = BooleanField(
        required=False,
        label="Create stock device",
    )

    def __init__(self, *args, **kwargs):
        kwargs.pop('mode')
        exclude = kwargs.pop('exclude', None)
        super(DeviceForm, self).__init__(*args, **kwargs)
        self.fields['ralph_device_id'] = AutoCompleteSelectField(
            LOOKUPS['ralph_device'],
            required=False,
            help_text='Enter ralph id, barcode, sn, or model.',
        )
        if exclude == 'create_stock':
            del self.fields['create_stock']

    def clean_ralph_device_id(self):
        return self.data['ralph_device_id'] or None

    def clean_create_stock(self):
        create_stock = self.cleaned_data.get('create_stock', False)
        if create_stock:
            if not self.cleaned_data.get('ralph_device_id'):
                return create_stock
            else:
                raise ValidationError(
                    _("'Ralph device id' field should be blank")
                )
        else:
            return create_stock

    def clean(self):
        ralph_device_id = self.cleaned_data.get('ralph_device_id')
        force_unlink = self.cleaned_data.get('force_unlink')
        if ralph_device_id:
            device_info = None
            try:
                device_info = self.instance.__class__.objects.get(
                    ralph_device_id=ralph_device_id
                )
            except DeviceInfo.DoesNotExist:
                pass
            if device_info:
                # if we want to assign ralph_device_id that belongs to another
                # Asset/DeviceInfo...
                if (str(device_info.ralph_device_id) == ralph_device_id and
                        device_info.id != self.instance.id):
                    if force_unlink:
                        device_info.ralph_device_id = None
                        device_info.save()
                    else:
                        msg = _(
                            'Device with this Ralph device id already exist '
                            '<a href="../{}">(click here to see it)</a>. '
                            'Please tick "Force unlink" checkbox if you want '
                            'to unlink it.'
                        )
                        self._errors["ralph_device_id"] = self.error_class([
                            mark_safe(msg.format(escape(device_info.asset.id)))
                        ])
        return self.cleaned_data


class BasePartForm(ModelForm):
    class Meta:
        model = PartInfo
        fields = ('barcode_salvaged',)

    def __init__(self, *args, **kwargs):
        """mode argument is required for distinguish ajax sources"""
        mode = kwargs.get('mode')
        if mode:
            del kwargs['mode']
        else:
            raise ModeNotSetException("mode argument not given.")
        super(BasePartForm, self).__init__(*args, **kwargs)

        channel = 'asset_dcdevice' if mode == 'dc' else 'asset_bodevice'
        self.fields['device'] = AutoCompleteSelectField(
            LOOKUPS[channel],
            required=False,
            help_text='Enter barcode, sn, or model.',
        )
        self.fields['source_device'] = AutoCompleteSelectField(
            LOOKUPS[channel],
            required=False,
            help_text='Enter barcode, sn, or model.',
        )
        if self.instance.source_device:
            self.fields[
                'source_device'
            ].initial = self.instance.source_device.id
        if self.instance.device:
            self.fields['device'].initial = self.instance.device.id


def _validate_multivalue_data(data):
    '''
        Check if data is a correct string with serial numbers and split
        it to list

        :param string: string with serial numbers splited by new line or comma
        :return list: list of serial numbers
    '''
    error_msg = _("Field can't be empty. Please put the items separated "
                  "by new line or comma.")
    data = data.strip()
    if not data:
        raise ValidationError(error_msg)
    items = []
    for item in filter(len, re.split(",|\n", data)):
        item = item.strip()
        if item in items:
            raise ValidationError(
                _("There are duplicate serial numbers in field.")
            )
        elif ' ' in item:
            raise ValidationError(
                _("Serial number can't contain white characters.")
            )
        elif item:
            items.append(item)
    if not items:
        raise ValidationError(error_msg)
    return items


def _check_field_uniqueness(field_path, values):
    '''
        Check field (pointed by *field_path*) uniqueness.
        If duplicated value is found then return false status with information
        about not unique ids

        :param string field_path: model field to be unique (as a string)
        :param list values: list of field values
        :return tuple: status and not unique ids or empty list
        :rtype tuple:
    '''
    conditions = {
        '{}__in'.format(field_path): values
    }
    assets = Asset.objects.filter(**conditions)
    if not assets:
        return True, []
    not_unique = []
    for asset in assets:
        last_field = asset
        for field_name in field_path.split('__'):
            last_field = getattr(last_field, field_name)
        not_unique.append((last_field, asset.id, asset.type))
    return False, not_unique


def _check_serial_numbers_uniqueness(serial_numbers):
    '''
        Check serial numbers uniqueness. If find any not unique
        serial number then return false status with information
        about not unique serial numbers

        :param list serial_numbers: list of serial numbers
        :return tuple: status and not unique serial numbers or empty list
        :rtype tuple:
    '''
    status, duplicated = _check_field_uniqueness('sn', serial_numbers)
    return status, duplicated


def _check_barcodes_uniqueness(barcodes):
    '''
        Check barcodes uniqueness. If find any not unique
        barcode then return false status with information
        about not unique barcode

        :param list barcodes: list of barcodes
        :return tuple: status and not unique barcodes or empty list
        :rtype tuple:
    '''
    status, duplicated = _check_field_uniqueness('barcode', barcodes)
    return status, duplicated


def _check_imeis_uniqueness(imeis):
    '''
        Check imei uniqueness. If find any not unique
        imei then return false status with information
        about not unique imei

        :param list imeis: list of imeis
        :return tuple: status and not unique imeis or empty list
        :rtype tuple:
    '''
    status, duplicated = _check_field_uniqueness('office_info__imei', imeis)
    return status, duplicated


def _sn_additional_validation(serial_numbers):
    '''
        Raise ValidationError if any of serial numbers is not unique

        :param list serial_numbers: list of serial numbers
    '''
    is_unique, not_unique_sn = _check_serial_numbers_uniqueness(serial_numbers)
    if not is_unique:
        # ToDo: links to assets with duplicate sn
        msg = "Following serial number already exists in DB: %s" % (
            ", ".join(item[0] for item in not_unique_sn)
        )
        raise ValidationError(msg)


class DependencyAssetForm(DependencyForm):
    """
    Containts common solution for adding asset and editing asset section.
    Launches a plugin which depending on the category field gives the
    opportunity to complete fields such as slots
    """

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            initial = kwargs.setdefault('initial', {})
            initial['licences'] = [
                licence['pk']
                for licence in kwargs['instance'].licence_set.values('pk')
            ]
        super(DependencyAssetForm, self).__init__(*args, **kwargs)

    @property
    def dependencies(self):
        """
        On the basis of data from the database gives the opportunity
        to complete fields such as slots

        :returns object: Logic to test if category is in selected categories
        :rtype object:
        """
        deps = [
            Dependency(
                'slots',
                'category',
                dependency_conditions.MemberOf(
                    AssetCategory.objects.filter(is_blade=True).all()
                ),
                SHOW,
            ),
            Dependency(
                'imei',
                'category',
                dependency_conditions.MemberOf(
                    AssetCategory.objects.filter(pk__in=[
                        "1-1-back-office-mobile-devices",
                        "1-1-1-back-office-mobile-devices-mobile-phone",
                        "1-1-1-back-office-mobile-devices-smartphone",
                        "1-1-1-back-office-mobile-devices-tablet",
                    ]).all()
                ),
                SHOW,
            ),
            Dependency(
                'imei',
                'category',
                dependency_conditions.MemberOf(
                    AssetCategory.objects.filter(pk__in=[
                        "1-1-back-office-mobile-devices",
                        "1-1-1-back-office-mobile-devices-mobile-phone",
                        "1-1-1-back-office-mobile-devices-smartphone",
                    ]).all()
                ),
                REQUIRE,
            ),
            Dependency(
                'location',
                'owner',
                dependency_conditions.NotEmpty(),
                AJAX_UPDATE,
                url=reverse('category_dependency_view'),
                page_load_update=False,
            ),
            Dependency(
                'loan_end_date',
                'status',
                dependency_conditions.Exact(AssetStatus.loan.id),
                SHOW,
            ),
            Dependency(
                'loan_end_date',
                'status',
                dependency_conditions.Exact(AssetStatus.loan.id),
                REQUIRE,
            ),
            Dependency(
                'note',
                'status',
                dependency_conditions.Exact(AssetStatus.loan.id),
                SHOW,
            ),
            Dependency(
                'niw',
                'barcode',
                dependency_conditions.NotEmpty(),
                CLONE,
                page_load_update=False,
            ),
            Dependency(
                'owner',
                'user',
                dependency_conditions.NotEmpty(),
                CLONE,
                page_load_update=False,
            ),
        ]
        ad_fields = (
            'company',
            'employee_id',
            'cost_center',
            'profit_center',
            'department',
            'manager',
        )
        deps.extend(
            [
                Dependency(
                    slave,
                    'owner',
                    dependency_conditions.NotEmpty(),
                    AJAX_UPDATE,
                    url=reverse('category_dependency_view'),
                ) for slave in ad_fields
            ]
        )
        deps.extend(
            [
                Dependency(
                    slave,
                    'owner',
                    dependency_conditions.NotEmpty(),
                    SHOW,
                ) for slave in ad_fields
            ]
        )
        for dep in deps:
            yield dep


class BaseAddAssetForm(DependencyAssetForm, ModelForm):
    '''
        Base class to display form used to add new asset
    '''

    class Meta:
        model = Asset
        fields = (
            'niw',
            'type',
            'category',
            'imei',
            'model',
            'status',
            'task_url',
            'warehouse',
            'property_of',
            'source',
            'invoice_no',
            'order_no',
            'price',
            'support_price',
            'support_type',
            'support_period',
            'support_void_reporting',
            'provider',
            'remarks',
            'service_name',
            'request_date',
            'provider_order_date',
            'delivery_date',
            'invoice_date',
            'production_use_date',
            'deprecation_rate',
            'force_deprecation',
            'slots',
            'production_year',
            'user',
            'owner',
            'location',
            'company',
            'employee_id',
            'cost_center',
            'profit_center',
            'department',
            'manager',
            'loan_end_date',
            'note',
        )
        widgets = {
            'request_date': DateWidget(),
            'delivery_date': DateWidget(),
            'invoice_date': DateWidget(),
            'production_use_date': DateWidget(),
            'provider_order_date': DateWidget(),
            'remarks': Textarea(attrs={'rows': 3}),
            'support_type': Textarea(attrs={'rows': 5}),
            'loan_end_date': DateWidget(),
            'note': Textarea(attrs={'rows': 3}),
        }
    model = AutoCompleteSelectField(
        LOOKUPS['asset_model'],
        required=True,
        plugin_options=dict(
            add_link='/admin/ralph_assets/assetmodel/add/?name=',
        )
    )
    licences = AutoCompleteSelectMultipleField(
        LOOKUPS['free_licences'],
        required=False,
    )
    warehouse = AutoCompleteSelectField(
        LOOKUPS['asset_warehouse'],
        required=True,
        plugin_options=dict(
            add_link='/admin/ralph_assets/warehouse/add/?name=',
        )
    )
    category = TreeNodeChoiceField(
        queryset=AssetCategory.tree.all(),
        level_indicator='|---',
        empty_label="---",
    )
    source = ChoiceField(
        required=False,
        choices=[('', '----')] + AssetSource(),
    )
    imei = CharField(
        min_length=15, max_length=18, validators=[validate_imei],
        label=_("IMEI"), required=False,
    )
    owner = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=False,
    )
    location = CharField(required=False)
    company = CharField(
        max_length=64,
        required=False,
    )
    employee_id = CharField(
        max_length=64,
        required=False,
    )
    cost_center = CharField(
        max_length=1024,
        required=False,
    )
    profit_center = CharField(
        max_length=1024,
        required=False,
    )
    department = CharField(
        max_length=64,
        required=False,
    )
    manager = CharField(
        max_length=1024,
        required=False,
    )
    user = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.fieldsets = asset_fieldset()

        mode = kwargs.get('mode')
        if mode:
            del kwargs['mode']
        super(BaseAddAssetForm, self).__init__(*args, **kwargs)

        category = self.fields['category'].queryset
        if mode == "dc":
            self.fields['model'].widget.plugin_options['add_link'] +=\
                '&type=' + str(AssetType.data_center.id)
            self.fields['model'].widget.channel = LOOKUPS['asset_dcmodel']
            self.fields['type'].choices = [
                (c.id, c.desc) for c in AssetType.DC.choices]
            self.fields['category'].queryset = category.filter(
                type=AssetCategoryType.data_center
            )
        elif mode == "back_office":
            self.fields['model'].widget.plugin_options['add_link'] +=\
                '&type=' + str(AssetType.back_office.id)
            self.fields['model'].widget.channel = LOOKUPS['asset_bomodel']
            self.fields['type'].choices = [
                (c.id, c.desc) for c in AssetType.BO.choices]
            self.fields['category'].queryset = category.filter(
                type=AssetCategoryType.back_office
            )

        for readonly_field in (
            'company',
            'employee_id',
            'cost_center',
            'profit_center',
            'department',
            'manager',
        ):
            self.fields[readonly_field].widget = ReadOnlyWidget()

    def clean_category(self):
        data = self.cleaned_data["category"]
        if not data.parent:
            raise ValidationError(
                _("Category must be selected from the subcategory")
            )
        return data

    def clean_imei(self):
        return self.cleaned_data['imei'] or None

    def clean_production_year(self):
        return validate_production_year(self)


class BaseEditAssetForm(DependencyAssetForm, ModelForm):
    '''
        Base class to display form used to edit asset
    '''

    class Meta:
        model = Asset
        fields = (
            'niw',
            'sn',
            'type',
            'category',
            'imei',
            'model',
            'status',
            'task_url',
            'warehouse',
            'property_of',
            'source',
            'invoice_no',
            'order_no',
            'price',
            'support_price',
            'support_type',
            'support_period',
            'support_void_reporting',
            'provider',
            'remarks',
            'service_name',
            'sn',
            'barcode',
            'request_date',
            'provider_order_date',
            'delivery_date',
            'invoice_date',
            'production_use_date',
            'deleted',
            'deprecation_rate',
            'force_deprecation',
            'slots',
            'production_year',
            'user',
            'owner',
            'location',
            'company',
            'employee_id',
            'cost_center',
            'profit_center',
            'department',
            'manager',
            'loan_end_date',
            'note',
        )
        widgets = {
            'request_date': DateWidget(),
            'delivery_date': DateWidget(),
            'invoice_date': DateWidget(),
            'production_use_date': DateWidget(),
            'provider_order_date': DateWidget(),
            'remarks': Textarea(attrs={'rows': 3}),
            'support_type': Textarea(attrs={'rows': 5}),
            'sn': Textarea(attrs={'rows': 1, 'readonly': '1'}),
            'barcode': Textarea(attrs={'rows': 1}),
            'loan_end_date': DateWidget(),
            'note': Textarea(attrs={'rows': 3}),
        }
    model = AutoCompleteSelectField(
        LOOKUPS['asset_model'],
        required=True,
        plugin_options=dict(
            add_link='/admin/ralph_assets/assetmodel/add/?name=',
        )
    )
    licences = AutoCompleteSelectMultipleField(
        LOOKUPS['free_licences'],
        required=False,
    )
    warehouse = AutoCompleteSelectField(
        LOOKUPS['asset_warehouse'],
        required=True,
        plugin_options=dict(
            add_link='/admin/ralph_assets/warehouse/add/?name=',
        )
    )
    category = TreeNodeChoiceField(
        queryset=AssetCategory.tree.all(),
        level_indicator='|---',
        empty_label="---",
    )
    source = ChoiceField(
        required=False,
        choices=[('', '----')] + AssetSource(),
    )
    imei = CharField(
        min_length=15, max_length=18, validators=[validate_imei],
        label=_("IMEI"), required=False,
    )
    user = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=False,
    )
    owner = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=False,
    )
    location = CharField(required=False)
    company = CharField(
        max_length=64,
        required=False,
    )
    employee_id = CharField(
        max_length=64,
        required=False,
    )
    cost_center = CharField(
        max_length=1024,
        required=False,
    )
    profit_center = CharField(
        max_length=1024,
        required=False,
    )
    department = CharField(
        max_length=64,
        required=False,
    )
    manager = CharField(
        max_length=1024,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.fieldsets = asset_fieldset()

        mode = kwargs.get('mode')
        if mode:
            del kwargs['mode']
        super(BaseEditAssetForm, self).__init__(*args, **kwargs)
        category = self.fields['category'].queryset
        if mode == "dc":
            self.fields['type'].choices = [
                (c.id, c.desc) for c in AssetType.DC.choices]
            self.fields['category'].queryset = category.filter(
                type=AssetCategoryType.data_center
            )
        elif mode == "back_office":
            self.fields['type'].choices = [
                (c.id, c.desc) for c in AssetType.BO.choices]
            self.fields['category'].queryset = category.filter(
                type=AssetCategoryType.back_office
            )

        for readonly_field in (
            'company',
            'employee_id',
            'cost_center',
            'profit_center',
            'department',
            'manager',
        ):
            self.fields[readonly_field].widget = ReadOnlyWidget()

    def clean_sn(self):
        return self.instance.sn

    def clean_category(self):
        data = self.cleaned_data["category"]
        if not data.parent:
            raise ValidationError(
                _("Category must be selected from the subcategory")
            )
        return data

    def clean_production_year(self):
        return validate_production_year(self)

    def clean_imei(self):
        return self.cleaned_data['imei'] or None

    def clean(self):
        if self.instance.deleted:
            raise ValidationError(_("Cannot edit deleted asset"))
        cleaned_data = super(BaseEditAssetForm, self).clean()
        return cleaned_data


def validate_production_year(asset):
    data = asset.cleaned_data["production_year"]
    if data is None:
        return data
    # Matches any 4-digit number:
    year_re = re.compile('^\d{4}$')
    if not year_re.match(str(data)):
        raise ValidationError(u'%s is not a valid year.' % data)
    # Check not before this year:
    year = int(data)
    thisyear = time.localtime()[0]
    if year > thisyear:
        raise ValidationError(
            u'%s is a year in the future.'
            u' Please enter a current or past year.' % data)
    return data


class MoveAssetPartForm(Form):
    new_asset = AutoCompleteSelectField(
        LOOKUPS['asset_dcdevice'],
    )


class AddPartForm(BaseAddAssetForm):
    '''
        Add new part for device
    '''
    sn = CharField(
        label=_("SN/SNs"), required=True, widget=Textarea(attrs={'rows': 25}),
    )

    def __init__(self, *args, **kwargs):
        super(AddPartForm, self).__init__(*args, **kwargs)
        self.fieldsets = asset_fieldset()
        self.fieldsets['Basic Info'].remove('barcode')

    def clean_sn(self):
        data = _validate_multivalue_data(self.cleaned_data["sn"])
        _sn_additional_validation(data)
        return data


class AddDeviceForm(BaseAddAssetForm):
    '''
        Add new device form
    '''
    sn = CharField(
        label=_("SN/SNs"), required=True, widget=Textarea(attrs={'rows': 25}),
    )
    barcode = CharField(
        label=_("Barcode/Barcodes"), required=False,
        widget=Textarea(attrs={'rows': 25}),
    )
    imei = CharField(
        label=_("IMEI"), required=False,
        widget=Textarea(attrs={'rows': 25}),
    )

    def __init__(self, *args, **kwargs):
        super(AddDeviceForm, self).__init__(*args, **kwargs)

    def clean_sn(self):
        '''
            Validate if sn is correct and change string with serial numbers
            to list
        '''
        data = _validate_multivalue_data(self.cleaned_data["sn"])
        _sn_additional_validation(data)
        return data

    def clean_barcode(self):
        data = self.cleaned_data["barcode"].strip()
        barcodes = []
        if data:
            for barcode in filter(len, re.split(",|\n", data)):
                barcode = barcode.strip()
                if barcode in barcodes:
                    raise ValidationError(
                        _("There are duplicate barcodes in the field.")
                    )
                elif ' ' in barcode:
                    raise ValidationError(
                        _("Serial number can't contain white characters.")
                    )
                elif barcode:
                    barcodes.append(barcode)
            if not barcodes:
                raise ValidationError(_("Barcode list could be empty or "
                                        "must have the same number of "
                                        "items as a SN list."))
            is_unique, not_unique_bc = _check_barcodes_uniqueness(barcodes)
            if not is_unique:
                # ToDo: links to assets with duplicate barcodes
                msg = "Following barcodes already exists in DB: %s" % (
                    ", ".join(item[0] for item in not_unique_bc)
                )
                raise ValidationError(msg)
        return barcodes

    def clean_imei(self):
        imeis = []
        data = self.cleaned_data['imei'].strip()
        if data:
            for imei in filter(len, re.split(",|\n", data)):
                imei = imei.strip()
                if imei in imeis:
                    raise ValidationError(
                        _("There are duplicate IMEIs in the field.")
                    )
                elif validate_imei(imei):
                    # Exception raised by validator
                    pass
                imeis.append(imei)
            is_unique, not_unique_bc = _check_imeis_uniqueness(imeis)
            if not is_unique:
                # ToDo: links to assets with duplicate imeis
                msg = "Following IMEIs already exists in DB: %s" % (
                    ", ".join(item[0] for item in not_unique_bc)
                )
                raise ValidationError(msg)
        return imeis

    def clean(self):
        cleaned_data = super(AddDeviceForm, self).clean()
        serial_numbers = cleaned_data.get("sn", [])
        barcodes = cleaned_data.get("barcode", [])
        imeis = cleaned_data.get("imei", None)
        if barcodes and len(serial_numbers) != len(barcodes):
            self._errors["barcode"] = self.error_class([
                _("Barcode list could be empty or must have the same number "
                  "of items as a SN list.")
            ])
        if imeis and len(serial_numbers) != len(imeis):
            self._errors["imei"] = self.error_class([
                _("IMEI list could be empty or must have the same number "
                  "of items as a SN list.")
            ])
        return cleaned_data


class BackOfficeAddDeviceForm(AddDeviceForm):

    purpose = ChoiceField(
        choices=[('', '----')] + models_assets.AssetPurpose(),
        label='Purpose',
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super(BackOfficeAddDeviceForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = move_after(
            self.fields.keyOrder, 'warehouse', 'purpose'
        )


class DataCenterAddDeviceForm(AddDeviceForm):
    pass


class OfficeForm(ModelForm):
    class Meta:
        model = OfficeInfo
        exclude = ('imei', 'purpose', 'created', 'modified')
        widgets = {
            'date_of_last_inventory': DateWidget(),
        }


class EditPartForm(BaseEditAssetForm):
    pass


class EditDeviceForm(BaseEditAssetForm):
    def clean(self):
        cleaned_data = super(EditDeviceForm, self).clean()
        deleted = cleaned_data.get("deleted")
        if deleted and self.instance.has_parts():
            parts = self.instance.get_parts_info()
            raise ValidationError(
                _(
                    "Cannot remove asset with parts assigned. Please remove "
                    "or unassign them from device first. ".format(
                        ", ".join([part.asset.sn for part in parts])
                    )
                )
            )
        if not cleaned_data.get('sn') and not cleaned_data.get('barcode'):
            raise ValidationError(
                _("If SN is empty - Barcode is required")
            )
        return cleaned_data


class BackOfficeEditDeviceForm(EditDeviceForm):

    purpose = ChoiceField(
        choices=[('', '----')] + models_assets.AssetPurpose(),
        label='Purpose',
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super(BackOfficeEditDeviceForm, self).__init__(*args, **kwargs)
        self.fieldsets = asset_fieldset()
        for after, field in (
            ('sn', 'imei'),
            ('loan_end_date', 'purpose'),
        ):
            self.fieldsets['Basic Info'].append(field)
            move_after(self.fieldsets['Basic Info'], after, field)


class DataCenterEditDeviceForm(EditDeviceForm):

    def __init__(self, *args, **kwargs):
        super(DataCenterEditDeviceForm, self).__init__(*args, **kwargs)
        self.fieldsets = asset_fieldset()
        for after, field in (
            ('status', 'slots'),
        ):
            self.fieldsets['Basic Info'].append(field)
            move_after(self.fieldsets['Basic Info'], after, field)


class SearchAssetForm(Form):
    """returns search asset form for DC and BO.

    :param mode: one of `dc` for DataCenter or `bo` for Back Office
    :returns Form
    """
    model = AutoCompleteField(
        LOOKUPS['asset_model'],
        required=False,
        help_text=None,
    )
    manufacturer = AutoCompleteField(
        LOOKUPS['asset_manufacturer'],
        required=False,
        help_text=None,
    )
    invoice_no = CharField(required=False)
    order_no = CharField(required=False)
    provider = CharField(required=False, label='Provider')
    status = ChoiceField(
        required=False, choices=[('', '----')] + AssetStatus(),
        label='Status'
    )
    task_url = CharField(required=False, label='Task url')
    owner = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=False,
    )
    user = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=False,
    )
    location = CharField(required=False, label='Location')
    company = CharField(required=False, label='Company')
    employee_id = CharField(required=False, label='Employee id')
    cost_center = CharField(required=False, label='Cost center')
    profit_center = CharField(required=False, label='Profit center')
    department = CharField(required=False, label='Department')
    part_info = ChoiceField(
        required=False,
        choices=[('', '----'), ('device', 'Device'), ('part', 'Part')],
        label='Asset type'
    )
    category = TreeNodeChoiceField(
        required=False,
        queryset=AssetCategory.tree.all(),
        level_indicator='|---',
        empty_label="---",
    )
    source = ChoiceField(
        required=False,
        choices=[('', '----')] + AssetSource(),
    )
    niw = CharField(required=False, label='Inventory number')
    sn = CharField(required=False, label='SN')
    barcode = CharField(required=False, label='Barcode')
    ralph_device_id = IntegerField(
        required=False,
        label='Ralph device id',
    )
    request_date_from = DateField(
        required=False, widget=DateWidget(attrs={
            'placeholder': 'Start YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label="Request date",
        input_formats=RALPH_DATE_FORMAT,
    )
    request_date_to = DateField(
        required=False, widget=DateWidget(attrs={
            'class': 'end-date-field ',
            'placeholder': 'End YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label='',
        input_formats=RALPH_DATE_FORMAT,
    )
    provider_order_date_from = DateField(
        required=False, widget=DateWidget(attrs={
            'placeholder': 'Start YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label="Provider order date",
        input_formats=RALPH_DATE_FORMAT,
    )
    provider_order_date_to = DateField(
        required=False, widget=DateWidget(attrs={
            'class': 'end-date-field ',
            'placeholder': 'End YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label='',
        input_formats=RALPH_DATE_FORMAT,
    )
    delivery_date_from = DateField(
        required=False, widget=DateWidget(attrs={
            'placeholder': 'Start YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label="Delivery date",
        input_formats=RALPH_DATE_FORMAT,
    )
    delivery_date_to = DateField(
        required=False, widget=DateWidget(attrs={
            'class': 'end-date-field ',
            'placeholder': 'End YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label='',
        input_formats=RALPH_DATE_FORMAT,
    )
    deprecation_rate = ChoiceField(
        required=False, choices=[('', '----'),
                                 ('null', 'None'),
                                 ('48>', '48 <'),
                                 ('48', '24 < * <= 48'),
                                 ('24', '12 < * <= 24'),
                                 ('12', '6 < * <= 12'),
                                 ('6', '* <= 6'),
                                 ('deprecated', 'Deprecated'), ],
        label='Deprecation'
    )
    invoice_date_from = DateField(
        required=False, widget=DateWidget(attrs={
            'placeholder': 'Start YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label="Invoice date",
        input_formats=RALPH_DATE_FORMAT,
    )
    invoice_date_to = DateField(
        required=False, widget=DateWidget(attrs={
            'class': 'end-date-field ',
            'placeholder': 'End YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label='',
        input_formats=RALPH_DATE_FORMAT,
    )

    production_use_date_from = DateField(
        required=False, widget=DateWidget(attrs={
            'placeholder': 'Start YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label="Production use date",
        input_formats=RALPH_DATE_FORMAT,
    )
    production_use_date_to = DateField(
        required=False, widget=DateWidget(attrs={
            'class': 'end-date-field ',
            'placeholder': 'End YYYY-MM-DD',
            'data-collapsed': True,
        }),
        label='')
    unlinked = BooleanField(required=False, label="Is unlinked")
    deleted = BooleanField(required=False, label="Include deleted")
    loan_end_date_from = DateField(
        required=False, widget=DateWidget(attrs={
            'placeholder': _('Start YYYY-MM-DD'),
            'data-collapsed': True,
        }),
        label=_("Loan end date"),
        input_formats=RALPH_DATE_FORMAT,
    )
    loan_end_date_to = DateField(
        required=False, widget=DateWidget(attrs={
            'class': 'end-date-field ',
            'placeholder': _('End YYYY-MM-DD'),
            'data-collapsed': True,
        }),
        label='',
        input_formats=RALPH_DATE_FORMAT,
    )
    service_name = ModelChoiceField(
        queryset=Service.objects.all(), empty_label="----", required=False,
    )

    def __init__(self, *args, **kwargs):
        # Ajax sources are different for DC/BO, use mode for distinguish
        mode = kwargs.get('mode')
        if mode:
            del kwargs['mode']
        super(SearchAssetForm, self).__init__(*args, **kwargs)
        category = self.fields['category'].queryset
        if mode == 'dc':
            self.fields['category'].queryset = category.filter(
                type=AssetCategoryType.data_center
            )
        elif mode == 'back_office':
            self.fields['category'].queryset = category.filter(
                type=AssetCategoryType.back_office
            )


class DataCenterSearchAssetForm(SearchAssetForm):
    pass


class BackOfficeSearchAssetForm(SearchAssetForm):
    imei = CharField(required=False, label='IMEI')
    purpose = ChoiceField(
        choices=[('', '----')] + models_assets.AssetPurpose(),
        label='Purpose',
        required=False,
    )


class DeleteAssetConfirmForm(Form):
    asset_id = IntegerField(widget=HiddenInput())


class SplitDevice(ModelForm):
    class Meta:
        model = Asset
        fields = (
            'id', 'delete', 'model_proposed', 'model_user', 'invoice_no',
            'order_no', 'sn', 'barcode', 'price', 'support_price',
            'support_period', 'support_type', 'support_void_reporting',
            'provider', 'source', 'status', 'request_date', 'delivery_date',
            'invoice_date', 'production_use_date', 'provider_order_date',
            'warehouse', 'production_year',
        )
        widgets = {
            'request_date': DateWidget(),
            'delivery_date': DateWidget(),
            'invoice_date': DateWidget(),
            'production_use_date': DateWidget(),
            'provider_order_date': DateWidget(),
            'device_info': HiddenInput(),
        }
    delete = BooleanField(required=False)
    model_user = CharField()
    model_proposed = CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(SplitDevice, self).__init__(*args, **kwargs)
        fillable_fields = [
            'model_user', 'device_info', 'invoice_no', 'order_no',
            'request_date', 'delivery_date', 'invoice_date',
            'production_use_date', 'provider_order_date',
            'provider_order_date', 'support_period', 'support_type',
            'provider', 'source', 'status', 'warehouse', 'production_year',
        ]
        for field_name in self.fields:
            if field_name in fillable_fields:
                classes = "span12 fillable"
            elif field_name == 'support_void_reporting':
                classes = ""
            else:
                classes = "span12"
            self.fields[field_name].widget.attrs = {'class': classes}
        self.fields['model_proposed'].widget = ReadOnlyWidget()

    def clean(self):
        cleaned_data = super(SplitDevice, self).clean()
        sn = cleaned_data.get('sn')
        barcode = cleaned_data.get('barcode')
        price = cleaned_data.get('price', '')
        try:
            float(price)
        except (ValueError, TypeError):
            if 'price' in self.errors:
                self.errors['price'].append(_("Price must be decimal"))
            else:
                self.errors['price'] = [_("Price must be decimal"), ]
        if not sn:
            cleaned_data['sn'] = None
        if not barcode:
            cleaned_data['barcode'] = None
        if not sn and not barcode:
            error_text = [_("SN or Barcode is required"), ]
            self.errors['sn'] = error_text
            self.errors['barcode'] = error_text
        return cleaned_data


class AttachmentForm(ModelForm):
    class Meta:
        model = models_assets.Attachment
        fields = ['file']


class UserRelationForm(Form):
    """A form that allows licence assignment for a user."""

    def __init__(self, user, *args, **kwargs):
        initial = kwargs.setdefault('initial', {})
        initial['licences'] = [
            licence['pk']
            for licence in user.licence_set.values('pk')
        ]
        super(UserRelationForm, self).__init__(*args, **kwargs)

    licences = AutoCompleteSelectMultipleField(
        LOOKUPS['free_licences'],
        required=False,
    )


class SearchUserForm(Form):
    """Form for left bar at the user_list view."""

    user = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=False,
    )
