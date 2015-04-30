# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.test import TestCase

from ralph.discovery.tests.util import DeviceFactory

from ralph_assets.api_ralph import (
    assign_asset,
    get_asset,
    get_asset_by_sn_or_barcode,
)
from ralph_assets.tests.utils.assets import (
    AssetCategoryFactory,
    AssetModelFactory,
    DCAssetFactory,
)
from ralph_assets.models_assets import Asset
from ralph_assets.tests.utils.supports import DCSupportFactory


class TestApiRalph(TestCase):
    """Test internal API for Ralph"""

    def test_get_asset(self):
        """Test get asset information by ralph_device."""
        support1 = DCSupportFactory()
        support2 = DCSupportFactory()
        category = AssetCategoryFactory()
        model = AssetModelFactory(category=category)
        asset = DCAssetFactory(
            model=model,
            supports=[support1, support2],
        )
        asset_data = get_asset(asset.device_info.ralph_device.id)
        self.assertEqual(asset_data['sn'], asset.sn)
        self.assertEqual(asset_data['barcode'], asset.barcode)
        self.assertEqual(asset_data['supports'][0]['name'], support1.name)
        self.assertEqual(
            asset_data['supports'][0]['url'],
            support1.get_absolute_url(),
        )
        self.assertEqual(asset_data['supports'][1]['name'], support2.name)
        self.assertEqual(
            asset_data['supports'][1]['url'],
            support2.get_absolute_url(),
        )
        self.assertEqual(
            asset_data['required_support'], asset.required_support,
        )

    def test_none_existisng_asset(self):
        """Getting an assets when assest does not exist"""
        self.assertEqual(get_asset(666), None)

    def test_get_asset_with_empty_asset_source(self):
        """Getting an asset with empty 'source' field should also succeed."""
        category = AssetCategoryFactory()
        model = AssetModelFactory(category=category)
        asset = DCAssetFactory(model=model, source=None)
        asset_data = get_asset(asset.device_info.ralph_device.id)
        self.assertEqual(asset_data['source'], None)

    def test_get_asset_by_sn_or_barcode(self):
        category = AssetCategoryFactory()
        model = AssetModelFactory(category=category)
        asset = DCAssetFactory(
            model=model,
        )
        # by sn
        asset_data = get_asset_by_sn_or_barcode(asset.sn)
        self.assertEqual(asset_data['sn'], asset.sn)
        self.assertEqual(asset_data['barcode'], asset.barcode)
        # by barcode
        asset_data = get_asset_by_sn_or_barcode(asset.barcode)
        self.assertEqual(asset_data['sn'], asset.sn)
        self.assertEqual(asset_data['barcode'], asset.barcode)
        # not exists
        self.assertEqual(get_asset_by_sn_or_barcode('foo_ziew_123'), None)


class TestAssetAssigning(TestCase):

    def test_unassigned_device_is_assigned_to_free_asset(self):
        """
        test unassigned device is assigned to asset (which is not paired with
        other device)
        """
        device = DeviceFactory()
        asset = DCAssetFactory()
        asset.device_info.ralph_device = None
        asset.device_info.save()

        self.assertIsNone(asset.device_info.ralph_device_id)
        result = assign_asset(device.id, asset.id)
        self.assertTrue(result)
        updated_asset = Asset.objects.get(pk=asset.id)
        self.assertEqual(updated_asset.device_info.ralph_device_id, device.id)

    def test_unassigned_device_is_assigned_to_paired_asset(self):
        """
        test unassigned device is assigned to asset (which is paired with
        another device)
        """
        asset = DCAssetFactory()
        device = DeviceFactory()

        self.assertNotEqual(
            asset.device_info.ralph_device_id, device.id,
        )
        result = assign_asset(device.id, asset.id)
        self.assertTrue(result)
        updated_asset = Asset.objects.get(pk=asset.id)
        self.assertEqual(updated_asset.device_info.ralph_device_id, device.id)

    def test_assigned_device_is_assigned_to_free_asset(self):
        """
        test assigned device is assigned to asset (which is not paired with
        other device)
        """
        old_pair = DCAssetFactory()
        device = old_pair.device_info.ralph_device
        asset = DCAssetFactory()
        asset.device_info.ralph_device = None
        asset.device_info.save()

        self.assertIsNotNone(old_pair.device_info.ralph_device)
        self.assertIsNone(asset.device_info.ralph_device)

        result = assign_asset(old_pair.device_info.ralph_device.id, asset.id)
        self.assertTrue(result)
        updated_old_pair = Asset.objects.get(pk=old_pair.id)
        updated_asset = Asset.objects.get(pk=asset.id)

        self.assertIsNone(updated_old_pair.device_info.ralph_device)
        self.assertEqual(updated_asset.device_info.ralph_device, device)

    def test_assigned_device_is_assigned_to_engaged_asset(self):
        """
        test assigned device is assigned to asset (which is paired with other
        device)
        """
        old_pair = DCAssetFactory()
        device = old_pair.device_info.ralph_device
        asset = DCAssetFactory()

        self.assertNotEqual(
            old_pair.device_info.ralph_device, asset.device_info.ralph_device,
        )

        result = assign_asset(old_pair.device_info.ralph_device.id, asset.id)
        self.assertTrue(result)
        updated_old_pair = Asset.objects.get(pk=old_pair.id)
        updated_asset = Asset.objects.get(pk=asset.id)

        self.assertIsNone(updated_old_pair.device_info.ralph_device)
        self.assertEqual(updated_asset.device_info.ralph_device, device)
