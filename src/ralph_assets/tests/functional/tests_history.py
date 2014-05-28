# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.test import TestCase

from ralph_assets.models_assets import (
    Asset,
    AssetStatus,
    LicenseType,
    SAVE_PRIORITY,
    AssetType
)
from ralph_assets.models_history import AssetHistoryChange
from ralph_assets.tests.utils.assets import (
    AssetCategoryFactory,
    AssetManufacturerFactory,
    AssetOwnerFactory,
    AssetModelFactory,
    WarehouseFactory,
)
from ralph.business.models import Venture
from ralph.discovery.models_device import Device, DeviceType
from ralph.ui.tests.global_utils import login_as_su


class HistoryAssetsView(TestCase):
    def setUp(self):
        self.client = login_as_su()
        self.category = AssetCategoryFactory()
        self.manufacturer = AssetManufacturerFactory()
        self.owner = AssetOwnerFactory()
        self.model = AssetModelFactory(
            manufacturer=self.manufacturer,
            category=self.category,
        )
        self.warehouse = WarehouseFactory()
        self.asset_params = {
            'type': 101,
            'model': self.model.id,
            'invoice_no': 123,
            'order_no': 1,
            'invoice_date': '2012-11-28',
            'support_period': 24,
            'support_type': 'standard',
            'support_void_reporting': 'on',
            'provider': 'test_provider',
            'property_of': self.owner.id,
            'status': AssetStatus.new.id,
            'remarks': 'test_remarks',
            'size': 1,
            'price': 10,
            'warehouse': self.warehouse.id,
            'sn': '666-666-666',
            'barcode': '666666',
            'asset': True,  # Button name
            'source': 1,
            'deprecation_rate': 0,
            'licences': '',
        }
        self.asset_change_params = {
            'barcode': '777777',
            'status': AssetStatus.damaged.id,
            'license_key': '66-66-66',
            'version': '0.1',
            'unit_price': 666.6,
            'license_type': LicenseType.oem.id,
            'date_of_last_inventory': '2012-11-08',
            'last_logged_user': 'ralph',
        }
        self.dc_asset_params = self.asset_params.copy()
        self.dc_asset_params.update({
            'slots': 1.0,
            'ralph_device_id': '',
            'production_year': 2011,
        })
        self.bo_asset_params = self.asset_params.copy()
        self.bo_asset_params.update({
            'purpose': 1,
            'coa_number': 2,
            'license_key': 3,
        })
        self.asset = None
        self.add_bo_device_asset()
        self.edit_bo_device_asset()

    def add_bo_device_asset(self):
        """Test check adding Asset into backoffice through the form UI"""
        url = '/assets/back_office/add/device/'
        attrs = self.bo_asset_params
        request = self.client.post(url, attrs)
        self.assertEqual(request.status_code, 302)

    def edit_bo_device_asset(self):
        """Test checks asset edition through the form UI"""
        self.asset = Asset.objects.get(barcode='666666')
        url = '/assets/back_office/edit/device/{}/'.format(self.asset.id)
        attrs = dict(
            self.bo_asset_params.items() + self.asset_change_params.items()
        )
        attrs.update({'purpose': 2})
        request = self.client.post(url, attrs)
        self.assertEqual(request.status_code, 302)

    def test_change_status(self):
        """Test check the recording Asset status change in asset history"""
        asset_history = AssetHistoryChange.objects.get(
            asset=self.asset, field_name='status'
        )
        self.assertListEqual(
            [asset_history.old_value, asset_history.new_value],
            [AssetStatus.new.name, AssetStatus.damaged.name]
        )

    def test_change_barcode(self):
        """Test check the recording Asset barcode change in asset history"""
        asset_history = AssetHistoryChange.objects.filter(
            asset=self.asset, field_name='barcode'
        )
        self.assertListEqual(
            [asset_history[0].old_value, asset_history[0].new_value],
            [self.asset_params['barcode'], self.asset_change_params['barcode']]
        )


class ConnectAssetWithDevice(TestCase):
    def setUp(self):
        self.client = login_as_su()
        self.category = AssetCategoryFactory()
        self.manufacturer = AssetManufacturerFactory()
        self.model = AssetModelFactory(
            manufacturer=self.manufacturer,
            category=self.category,
        )
        self.warehouse = WarehouseFactory()
        self.asset_params = {
            'type': AssetType.data_center.id,
            'model': self.model.id,
            'invoice_no': 666,
            'order_no': 2,
            'invoice_date': '2012-11-29',
            'provider': 'test_provider',
            'status': AssetStatus.new.id,
            'remarks': 'test_remarks',
            'price': 10,
            'warehouse': self.warehouse.id,
            'barcode': '7777',
            'source': 1,
            'deprecation_rate': 0,
            'production_year': 2011,
            'asset': True,  # Button name
        }
        self.dc_asset_params = self.asset_params.copy()
        self.dc_asset_params.update({
            'ralph_device_id': '',
            'slots': 0,
        })
        self.asset = None

    def test_add_dc_device_asset_with_create_device(self):
        """Test check situation, when Asset is created and
        the device is created with Asset serial_number
        """
        url = '/assets/dc/add/device/'
        attrs = self.dc_asset_params
        attrs['sn'] = '777-777',
        request = self.client.post(url, attrs)
        self.assertEqual(request.status_code, 302)
        asset = Asset.objects.get(sn='777-777')
        self.assertTrue(asset.device_info.ralph_device_id)
        device = Device.objects.get(id=asset.device_info.ralph_device_id)
        self.assertEqual(device.id, asset.device_info.ralph_device_id)
        self.assertEqual(device.model.name, 'Unknown')
        self.assertEqual(device.sn, '777-777')
        self.assertEqual(device.venture.name, 'Stock')

    def test_add_dc_device_asset_with_linked_device(self):
        """Test check situation, when Asset is created and device already
        exist with the same serial number as the Asset, then creates
        an link between the asset and the device
        """
        url = '/assets/dc/add/device/'
        attrs = self.dc_asset_params
        attrs['sn'] = '999-999',
        request = self.client.post(url, attrs)
        self.assertEqual(request.status_code, 302)
        asset = Asset.objects.get(sn='999-999')
        self.assertTrue(asset.device_info.ralph_device_id)
        device = Device.objects.get(id=asset.device_info.ralph_device_id)
        self.assertEqual(device.id, asset.device_info.ralph_device_id)

    def test_add_dc_device_asset_without_create_device(self):
        """Test check situation, when link beetwen the asset and the device
        is not created. This situation occurs when
        CONNECT_ASSET_WITH_DEVICE options set at False.
        """
        url = '/assets/dc/add/device/'
        attrs = self.dc_asset_params
        attrs['sn'] = '888-888',
        request = self.client.post(url, attrs)
        self.assertEqual(request.status_code, 302)


class TestsStockDevice(TestCase):
    def setUp(self):
        self.client = login_as_su()
        self.category = AssetCategoryFactory()
        self.manufacturer = AssetManufacturerFactory()
        self.model = AssetModelFactory(
            manufacturer=self.manufacturer,
            category=self.category,
        )
        self.warehouse = WarehouseFactory()
        self.asset_params = {
            'type': AssetType.data_center.id,
            'model': self.model.id,
            'warehouse': self.warehouse.id,
            'status': AssetStatus.new.id,
            'remarks': 'test_remarks',
            'order_no': 2,
            'invoice_date': '2012-11-29',
            'invoice_no': 00001,
            'price': 10,
            'provider': 'test_provider',
            'deprecation_rate': 0,
            'source': 1,
            'sn': 'fake-sn',
            'barcode': '7777',
            'asset': True,  # Button name
        }
        self.dc_asset_params = self.asset_params.copy()
        self.dc_asset_params.update({
            'ralph_device_id': '',
            'production_year': 2011,
            'slots': 0,
        })

    def create_device(self):
        venture = Venture(name='TestVenture', symbol='testventure')
        venture.save()
        Device.create(
            sn='000000001',
            model_name='test_model',
            model_type=DeviceType.unknown,
            priority=SAVE_PRIORITY,
            venture=venture,
            name='test_device',
        )
        return Device.objects.get(sn='000000001')

    def test_form_with_ralph_device_id(self):
        ralph_device = self.create_device()
        asset_params = self.asset_params
        asset_params['ralph_device_id'] = ralph_device.id
        request = self.client.post('/assets/dc/add/device/', asset_params)
        self.assertEqual(request.status_code, 302)
        asset = Asset.objects.get(sn='fake-sn')
        self.assertNotEqual(asset.sn, ralph_device.sn)
        self.assertEqual(asset.device_info.ralph_device_id, ralph_device.id)

    def test_form_with_sn(self):
        asset_device = self.create_device()
        asset_params = self.dc_asset_params
        asset_params['sn'] = '000000001'
        request = self.client.post('/assets/dc/add/device/', asset_params)
        self.assertEqual(request.status_code, 302)
        asset = Asset.objects.get(sn='000000001')
        self.assertEqual(asset.sn, asset_device.sn)
        self.assertEqual(asset.device_info.ralph_device_id, asset_device.id)

    def test_create_stock_device(self):
        asset_params = self.dc_asset_params
        request = self.client.post('/assets/dc/add/device/', asset_params)
        self.assertEqual(request.status_code, 302)
        asset = Asset.objects.get(sn='fake-sn')
        asset_device = Device.objects.get(sn='fake-sn')
        self.assertEqual(asset.sn, asset_device.sn)
        self.assertEqual(asset.device_info.ralph_device_id, asset_device.id)
