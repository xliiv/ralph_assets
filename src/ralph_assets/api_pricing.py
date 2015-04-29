# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db.models import Q

from ralph_assets.models_assets import Asset, Warehouse


def get_warehouses():
    """Yields dicts describing all warehouses"""
    for warehouse in Warehouse.objects.all():
        yield {
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
        }


def get_assets(date):
    """Yields dicts describing all assets"""
    for asset in Asset.objects_dc.filter(
        Q(invoice_date=None) | Q(invoice_date__lte=date),
        part_info=None,
    ):
        device_info = asset.device_info

        venture_info = asset.venture
        is_blade = None
        if asset.model and asset.model.category:
            is_blade = asset.model.category.is_blade

        yield {
            'asset_id': asset.id,
            'barcode': asset.barcode,
            'is_deprecated': asset.is_deprecated(date=date),
            'price': asset.price,
            'ralph_id': device_info.ralph_device.id if device_info else None,
            'slots': asset.slots,
            'sn': asset.sn,
            'price': asset.price,
            'deprecation_rate': asset.deprecation_rate,
            'power_consumption': asset.model.power_consumption,
            'height_of_device': asset.model.height_of_device,
            'warehouse_id': asset.warehouse_id,
            'venture_id': venture_info.id if venture_info else None,
            'is_blade': is_blade,
            'cores_count': asset.cores_count,
        }


def get_asset_parts():
    """Yields dicts describing parts of assets"""
    for asset in Asset.objects_dc.all():
        for part in asset.get_parts():
            device_info = asset.device_info
            yield {
                'asset_id': part.id,
                'barcode': asset.barcode,
                'is_deprecated': part.is_deprecated(),
                'model': part.model.name if part.model else None,
                'price': part.price,
                'ralph_id': device_info.ralph_device_id if device_info else None,  # noqa
                'sn': asset.sn,
                'deprecation_rate': asset.deprecation_rate,
                'is_deprecated': part.is_deprecated(),
            }
