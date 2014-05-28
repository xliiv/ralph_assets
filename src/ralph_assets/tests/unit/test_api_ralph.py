# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.test import TestCase

from ralph_assets.models import Asset, AssetCategory
from ralph_assets.tests.util import (
    create_asset,
    create_model,
    create_warehouse,
)


from ralph_assets.api_ralph import get_asset


class TestApiRalph(TestCase):
    """Test internal API for Ralph"""

    def setUp(self):
        self.category = AssetCategory.objects.get(name="Blade System")
        self.model = create_model(
            category=self.category
        )
        self.model2 = create_model(
            'Model2',
            category=self.category,
        )
        self.warehouse = create_warehouse()
        self.asset = create_asset(
            sn='1111-1111-1111-1111'
        )
        self.asset_id = self.asset.id
        self.asset.device_info.ralph_device_id = 666
        self.asset.device_info.save()

        self.asset_data_raw = {
            u'asset_id': 1,
            u'barcode': None,
            u'category': u'Blade System',
            u'delivery_date': None,
            u'deprecation_rate': 25,
            u'invoice_date': None,
            u'invoice_no': None,
            u'is_deprecated': True,
            u'manufacturer': u'Manufacturer1',
            u'model': u'Model1',
            u'niw': None,
            u'order_no': None,
            u'price': 0,
            u'production_use_date': None,
            u'provider': None,
            u'provider_order_date': None,
            u'rack': None,
            u'remarks': u'',
            u'request_date': None,
            u'size': 0,
            u'slots': 0.0,
            u'sn': u'1111-1111-1111-1111',
            u'source': u'shipment',
            u'status': u'new',
            u'support_period': 24,
            u'support_price': None,
            u'support_type': u'standard',
            u'support_void_reporting': True,
            u'u_height': None,
            u'u_level': None,
            u'warehouse': u'Warehouse',
        }

    def test_get_asset(self):
        """Test get asset information by ralph_device_id"""
        asset = Asset.objects.get(pk=self.asset_id)
        asset_data = get_asset(asset.device_info.ralph_device_id)
        self.assertEqual(asset_data, self.asset_data_raw)
