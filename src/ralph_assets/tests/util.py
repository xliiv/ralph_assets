# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.template.defaultfilters import slugify

from random import randint

from ralph_assets import models_assets
from ralph_assets.models_assets import (
    AssetCategory,
    AssetCategoryType,
    AssetModel,
    AssetSource,
    AssetStatus,
    AssetType,
    AssetManufacturer,
    DeviceInfo,
    Warehouse
)

import cgi

DEFAULT_ASSET_DATA = dict(
    manufacturer='Manufacturer1',
    model='Model1',
    power_consumption=100,
    height_of_device='D4',
    warehouse='Warehouse',
    type=AssetType.data_center,
    status=AssetStatus.new,
    source=AssetSource.shipment,
    category='Category1',
    asset_owner='AssetOwner',
    service_name='ServiceName',
)

DEFAULT_BO_VALUE = {
    'license_key': 'bo-license-key',
    'coa_number': 'bo-coa-number',
    'coa_oem_os': 'coa_oem_os',
    'imei': '1'*15,
    'purpose': models_assets.AssetPurpose.others,
}

SCREEN_ERROR_MESSAGES = dict(
    duplicated_sn_or_bc=cgi.escape((
        "Please correct errors and check both"
        "\"serial numbers\" and \"barcodes\" for duplicates"
    ), quote=True),
    duplicated_sn_in_field='There are duplicates in field.',
    contain_white_character="Item can't contain white characters.",
    django_required=(
        "Field can't be empty. Please put the item OR items separated "
        "by new line or comma."
    ),
    count_sn_and_bc="Fields: sn, barcode, imei - require the same count",
    barcode_already_exist='Following items already exist: ',
    empty_items_disallowed="Empty items disallowed, remove it.",
    any_required="SN or BARCODE field is required",
)


def create_manufacturer(name=DEFAULT_ASSET_DATA['manufacturer']):
    manufacturer, created = AssetManufacturer.objects.get_or_create(name=name)
    return manufacturer


def create_warehouse(name=DEFAULT_ASSET_DATA['warehouse']):
    warehouse, created = Warehouse.objects.get_or_create(name=name)
    return warehouse


def create_model(
    name=DEFAULT_ASSET_DATA['model'],
    manufacturer=None,
    category=DEFAULT_ASSET_DATA['category'],
):
    """name = string, manufacturer = string"""
    if not manufacturer:
        manufacturer = create_manufacturer()
    else:
        manufacturer = create_manufacturer(manufacturer)
    model, created = AssetModel.objects.get_or_create(name=name)
    if created:
        model.manufacturer = manufacturer
        if not isinstance(category, AssetCategory):
            try:
                category = AssetCategory.objects.get(pk=category)
            except AssetCategory.DoesNotExist:
                pass
            else:
                model.category = category
        else:
            model.category = category
        model.save()
    return model


def create_device(size=1):
    device = DeviceInfo(size=size)
    device.save()
    return device


def create_asset(sn, **kwargs):
    for field in ['status', 'source', 'type']:
        if field not in kwargs:
            kwargs[field] = DEFAULT_ASSET_DATA[field]
    if not kwargs.get('model'):
        kwargs.update(model=create_model())
    # TODO: make arg for DC|BO distinction
    if not kwargs.get('device_info'):
        kwargs.update(device_info=create_device())
    if not kwargs.get('support_period'):
        kwargs.update(support_period=24)
    if not kwargs.get('support_type'):
        kwargs.update(support_type='standard')
    if not kwargs.get('warehouse'):
        kwargs.update(warehouse=create_warehouse())
    db_object, created = models_assets.Asset.objects.get_or_create(
        sn=sn, defaults=kwargs
    )
    return db_object


def create_bo_asset(sn, **kwargs):
    """
    Creates asset with office_info data included in kwargs or with defaults
    """
    bo_data = {}
    for bo_field in 'license_key coa_number imei purpose'.split():
        if bo_field in kwargs:
            bo_value = kwargs.pop(bo_field)
        else:
            bo_value = DEFAULT_BO_VALUE[bo_field]
        bo_data[bo_field] = bo_value
    bo_info = models_assets.OfficeInfo(**bo_data)
    bo_info.save()
    kwargs['office_info'] = bo_info
    db_object = create_asset(sn, **kwargs)
    return db_object


def create_category(type='data_center', name=DEFAULT_ASSET_DATA['category']):
    subcategory_name = 'Subcategory'
    type_name = type
    if type == 'back_office':
        type = AssetCategoryType.back_office
    elif type == 'data_center':
        type = AssetCategoryType.data_center
    category = AssetCategory()
    category.name = name
    category.type = type
    category.slug = slugify(type_name + name)
    category.save()
    subcategory = AssetCategory()
    subcategory.name = subcategory_name
    subcategory.type = type
    subcategory.parent = category
    subcategory.slug = slugify(type_name + category.name + subcategory_name)
    subcategory.save()
    return subcategory


def get_bulk_edit_post_data_part(*args, **kwargs):
    id = kwargs.get('id')

    model_id = kwargs.get('model')
    if model_id is None:
        model = create_model()
        model_id = model.id

    sn = kwargs.get('sn')
    if sn is None:
        sn = '-'.join([str(randint(1000, 9999)) for i in xrange(4)])

    barcode = kwargs.get('barcode')
    if barcode is None:
        barcode = 'bc-{0}'.format(str(randint(1000, 9999)))

    warehouse = kwargs.get('warehouse')
    if warehouse is None:
        warehouse = create_warehouse()
        warehouse_id = warehouse.id

    return {
        'form-{0}-id'.format(id-1): id,
        'form-{0}-type'.format(id-1):
        kwargs.get('type', AssetType.data_center.id),
        'form-{0}-model'.format(id-1): model_id,
        'form-{0}-invoice_no'.format(id-1):
        kwargs.get('invoice_no', 'Invoice No0'),
        'form-{0}-invoice_date'.format(id-1):
        kwargs.get('invoice_date', '2014-01-01'),
        'form-{0}-order_no'.format(id-1):
        kwargs.get('order_no', 'Order No0'),
        'form-{0}-sn'.format(id-1): sn,
        'form-{0}-barcode'.format(id-1): barcode,
        'form-{0}-support_period'.format(id-1):
        kwargs.get('support_period', 24),
        'form-{0}-support_type'.format(id-1):
        kwargs.get('support_type', 'standard0'),
        'form-{0}-support_void_reporting'.format(id-1):
        kwargs.get('support_void_reporting', 'on'),
        'form-{0}-provider'.format(id-1):
        kwargs.get('provider', 'Provider 0'),
        'form-{0}-status'.format(id-1):
        kwargs.get('status', AssetStatus.in_progress.id),
        'form-{0}-source'.format(id-1):
        kwargs.get('source', AssetSource.shipment.id),
        'form-{0}-ralph_device_id'.format(id-1):
        kwargs.get('ralph_device_id', ''),
        'form-{0}-price'.format(id-1):
        kwargs.get('price', 10),
        'form-{0}-warehouse'.format(id-1): warehouse_id,
        'form-{0}-deprecation_rate'.format(id-1):
        kwargs.get('deprecation_rate', 25),
    }


def get_bulk_edit_post_data(*args, **kwargs):
    post_data = {
        'form-TOTAL_FORMS': u'{0}'.format(len(args)),
        'form-INITIAL_FORMS': u'{0}'.format(len(args)),
        'form-MAX_NUM_FORMS': u'',
    }
    for i, data in enumerate(args):
        data['id'] = i + 1
        post_data.update(get_bulk_edit_post_data_part(**data))
    return post_data


def create_user(username='user', defaults=None):
    if not defaults:
        defaults = {
            'username': username,
            'email': 'user@test.local',
            'is_staff': False,
            'first_name': 'Elmer',
            'last_name': 'Stevens',
        }
    db_object, created = models_assets.User.objects.get_or_create(
        username=username, defaults=defaults,
    )
    return db_object


def create_service(name=DEFAULT_ASSET_DATA['service_name']):
    db_object, created = models_assets.Service.objects.get_or_create(name=name)
    return db_object


def create_asset_owner(name=DEFAULT_ASSET_DATA['asset_owner']):
    db_object, created = models_assets.AssetOwner.objects.get_or_create(
        name=name
    )
    return db_object


def create_coaoemos(name=DEFAULT_BO_VALUE['coa_oem_os']):
    db_object, created = models_assets.CoaOemOs.objects.get_or_create(
        name=name
    )
    return db_object
