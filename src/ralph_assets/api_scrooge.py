# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from django.db.models import Q

from ralph.util.api import Getter
from ralph_assets.licences.models import Licence
from ralph_assets.models_assets import Asset, AssetModel, AssetType, Warehouse
from ralph_assets.models_support import Support

logger = logging.getLogger(__name__)


class DatedGetter(Getter):
    """
    Returns only items that have a timespan (marked by begin_field and
    end_field) that contains given date"""

    def __init__(self, date, *args, **kwargs):
        self.date = date
        super(DatedGetter, self).__init__(*args, **kwargs)

    def get_queryset(self):
        return super(DatedGetter, self).get_queryset().filter(**{
            self.begin_field + '__lte': self.date,
            self.end_field + '__gte': self.date,
        })


def get_warehouses():
    """Yields dicts describing all warehouses"""
    for warehouse in Warehouse.objects.all():
        yield {
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
        }


def get_models():
    for model in AssetModel.objects.filter(
        type__in=AssetType.DC.choices
    ).select_related('manufacturer', 'category'):
        yield {
            'model_id': model.id,
            'name': model.name,
            'manufacturer': (
                model.manufacturer.name if model.manufacturer else None
            ),
            'category': model.category.name if model.category else None,
        }


def get_assets(date):
    """Yields dicts describing all assets"""
    for asset in Asset.objects_dc.filter(
        Q(invoice_date=None) | Q(invoice_date__lte=date),
        part_info=None,
    ).select_related('model', 'device_info'):
        if not asset.device_info_id:
            logger.error('Asset {0} has no device'.format(asset.id))
            continue
        if not asset.service_id:
            logger.error('Asset {0} has no service'.format(asset.id))
            continue
        if not asset.device_environment_id:
            logger.error('Asset {0} has no environment'.format(asset.id))
            continue
        if asset.is_liquidated(date):
            logger.info("Skipping asset {} - it's liquidated")
            continue
        device_info = asset.device_info
        hostname = None
        ralph_device = None
        if device_info:
            ralph_device = device_info.get_ralph_device()
            if ralph_device:
                hostname = ralph_device.name
        try:
            data_center_id = asset.device_info.data_center_id
        except AttributeError:
            data_center_id = None

        yield {
            'asset_id': asset.id,
            'device_id': ralph_device.id if ralph_device else None,
            'asset_name': hostname,
            'service_id': asset.service_id,
            'environment_id': asset.device_environment_id,
            'sn': asset.sn,
            'barcode': asset.barcode,
            'warehouse_id': data_center_id,
            'cores_count': asset.cores_count,
            'power_consumption': asset.model.power_consumption,
            'collocation': asset.model.height_of_device,
            'depreciation_rate': asset.deprecation_rate,
            'is_depreciated': asset.is_deprecated(date=date),
            'price': asset.price,
            'model_id': asset.model_id,
        }


class get_supports(DatedGetter):
    """Gets data for DC supports."""

    Model = Support
    begin_field = 'date_from'
    end_field = 'date_to'

    filters = {'asset_type': AssetType.data_center, 'price__gt': 0}
    fields = [
        ('support_id', 'id'),
        'name',
        'price',
        'date_from',
        'date_to',
        ('assets', (lambda support: [
            asset.id for asset in support.assets.all()
        ]))
    ]


class get_licences(DatedGetter):
    """Gets data for DC licences."""

    Model = Licence
    begin_field = 'invoice_date'
    end_field = 'valid_thru'

    filters = {'asset_type': AssetType.data_center}

    fields = [
        ('software_category', 'software_category__name'),
        'price',
        'invoice_date',
        'valid_thru',
        ('assets', (lambda licence: [
            asset.id for asset in licence.assets.all()
        ]))
    ]
