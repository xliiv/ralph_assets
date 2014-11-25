# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.test import TestCase
from mock import patch

from ralph_assets.models_assets import DataCenter as AssetDataCenter
from ralph_assets.models_assets import ServerRoom as AssetServerRoom
from ralph_assets.models_assets import Rack as AssetRack
from ralph_assets.models_assets import DeviceInfo, Orientation
from ralph_assets.models_signals import (
    _update_cached_localization,
    _update_level_and_orientation,
    _update_localization,
    asset_device_info_post_save,
    update_core_localization,
)
from ralph_assets.tests.utils.assets import DCAssetFactory, DeviceInfoFactory
from ralph.discovery.models import DeviceType
from ralph.discovery.tests.util import DeviceModelFactory, DeviceFactory


class AssetDevInfoPostSaveTest(TestCase):

    def setUp(self):
        # core side
        self.dc_model = DeviceModelFactory(
            name="DC", type=DeviceType.data_center,
        )
        self.rack_model = DeviceModelFactory(
            name="Rack", type=DeviceType.rack,
        )
        self.dc_1 = DeviceFactory(name='DC1', sn='DC1', model=self.dc_model)
        self.dc_2 = DeviceFactory(name='DC2', sn='DC2', model=self.dc_model)
        self.rack_1_1 = DeviceFactory(
            name='Rack 1 DC1', sn='Rack 1 DC1', model=self.rack_model,
            parent=self.dc_1,
        )
        self.rack_1_2 = DeviceFactory(
            name='Rack 2 DC1', sn='Rack 2 DC1', model=self.rack_model,
            parent=self.dc_1,
        )
        self.rack_2_1 = DeviceFactory(
            name='Rack 1 DC2', sn='Rack 1 DC2', model=self.rack_model,
            parent=self.dc_1,
        )
        self.rack_2_2 = DeviceFactory(
            name='Rack 2 DC2', sn='Rack 2 DC2', model=self.rack_model,
            parent=self.dc_2,
        )
        self.dev_1 = DeviceFactory(name="h101.dc1", parent=self.rack_1_1)
        self.dev_2 = DeviceFactory(name="h201.dc1", parent=self.rack_1_2)
        self.dev_3 = DeviceFactory(name="h101.dc2", parent=self.rack_2_1)
        self.dev_4 = DeviceFactory(name="h201.dc2", parent=self.rack_2_2)
        # assets side
        self.assets_dc_1 = AssetDataCenter.objects.create(
            name='DC1', deprecated_ralph_dc_id=self.dc_1.id,
        )
        self.assets_dc_2 = AssetDataCenter.objects.create(
            name='DC2', deprecated_ralph_dc_id=self.dc_2.id,
        )
        self.assets_sr_1 = AssetServerRoom.objects.create(
            name="DC1_1", data_center=self.assets_dc_1,
        )
        self.assets_sr_2 = AssetServerRoom.objects.create(
            name="DC2_1", data_center=self.assets_dc_2,
        )
        self.assets_rack_1_1 = AssetRack.objects.create(
            name="Rack 1 DC1", deprecated_ralph_rack_id=self.rack_1_1.id,
            data_center=self.assets_dc_1,
        )
        self.assets_rack_1_2 = AssetRack.objects.create(
            name="Rack 2 DC1", deprecated_ralph_rack_id=self.rack_1_2.id,
            data_center=self.assets_dc_1,
        )
        self.assets_rack_2_1 = AssetRack.objects.create(
            name="Rack 1 DC2", deprecated_ralph_rack_id=self.rack_2_1.id,
            data_center=self.assets_dc_2,
        )
        self.assets_rack_2_2 = AssetRack.objects.create(
            name="Rack 2 DC2", deprecated_ralph_rack_id=self.rack_2_2.id,
            data_center=self.assets_dc_2,
        )
        self.assets_dev_1 = DCAssetFactory(
            device_info=DeviceInfoFactory(
                ralph_device_id=self.dev_1.id, data_center=self.assets_dc_1,
                server_room=self.assets_sr_1, rack=self.assets_rack_1_1,
            ),
        )
        self.assets_dev_2 = DCAssetFactory(
            device_info=DeviceInfoFactory(
                ralph_device_id=self.dev_2.id, data_center=self.assets_dc_1,
                server_room=self.assets_sr_1, rack=self.assets_rack_1_2,
            )
        )
        self.assets_dev_3 = DCAssetFactory(
            device_info=DeviceInfoFactory(
                ralph_device_id=self.dev_3.id, data_center=self.assets_dc_2,
                server_room=self.assets_sr_2, rack=self.assets_rack_2_1,
            )
        )
        self.assets_dev_4 = DCAssetFactory(
            device_info=DeviceInfoFactory(
                ralph_device_id=self.dev_4.id, data_center=self.assets_dc_2,
                server_room=self.assets_sr_2, rack=self.assets_rack_2_2,
                position=10, orientation=Orientation.front,
            )
        )

    def test_update_cached_localization(self):
        _update_cached_localization(
            device=self.dev_1, asset_dev_info=self.assets_dev_1.device_info,
        )
        self.assertEqual(self.dev_1.rack, 'Rack 1 DC1')
        self.assertEqual(self.dev_1.dc, 'DC1')
        _update_cached_localization(
            device=self.dev_3, asset_dev_info=self.assets_dev_3.device_info,
        )
        self.assertEqual(self.dev_3.rack, 'Rack 1 DC2')
        self.assertEqual(self.dev_3.dc, 'DC2')

    def test_update_localization(self):
        # case: blade server
        rack = AssetRack.objects.create(
            name="Rack 3 DC2", data_center=self.assets_dc_2,
        )
        old_device_info = self.assets_dev_2.device_info
        self.assets_dev_2.device_info = None
        self.assets_dev_2.save()
        old_device_info.delete()
        device_info = DeviceInfoFactory(
            ralph_device_id=self.dev_2.id, data_center=self.assets_dc_2,
            server_room=self.assets_sr_2, rack=rack,
        )
        self.assets_dev_2.device_info = device_info
        self.assets_dev_2.save()
        self.assets_dev_2.model.category.is_blade = True
        self.assets_dev_2.model.category.save()
        _update_localization(device=self.dev_2, asset_dev_info=device_info)
        self.assertEqual(self.dev_2.parent_id, self.rack_1_2.id)

        # case: device_info without deprecated_ralph_rack
        self.assets_dev_2.model.category.is_blade = False
        self.assets_dev_2.model.category.save()
        rack = AssetRack.objects.create(
            name="Rack 4 DC2", data_center=self.assets_dc_2,
        )
        old_device_info = self.assets_dev_2.device_info
        self.assets_dev_2.device_info = None
        self.assets_dev_2.save()
        old_device_info.delete()
        device_info = DeviceInfoFactory(
            ralph_device_id=self.dev_2.id, data_center=self.assets_dc_2,
            server_room=self.assets_sr_2, rack=rack,
        )
        self.assets_dev_2.device_info = device_info
        self.assets_dev_2.save()
        _update_localization(device=self.dev_2, asset_dev_info=device_info)
        self.assertEqual(self.dev_2.parent_id, self.rack_1_2.id)

        # case: rack and dc changed
        rack = AssetRack.objects.create(
            name="Rack 5 DC2", data_center=self.assets_dc_2,
            deprecated_ralph_rack_id=self.rack_2_2.id
        )
        old_device_info = self.assets_dev_2.device_info
        self.assets_dev_2.device_info = None
        self.assets_dev_2.save()
        old_device_info.delete()
        device_info = DeviceInfoFactory(
            ralph_device_id=self.dev_2.id, data_center=self.assets_dc_2,
            server_room=self.assets_sr_2, rack=rack,
        )
        self.assets_dev_2.device_info = device_info
        self.assets_dev_2.save()
        _update_localization(device=self.dev_2, asset_dev_info=device_info)
        self.assertEqual(self.dev_2.parent_id, self.rack_2_2.id)
        self.assertEqual(self.dev_2.parent.parent_id, self.dc_2.id)

    def test_update_level_and_orientation(self):
        _update_level_and_orientation(
            device=self.dev_4, asset_dev_info=self.assets_dev_4.device_info,
        )
        self.assertEqual(self.dev_4.chassis_position, 10)
        self.assertEqual(self.dev_4.position, 'front')

    @patch('ralph_assets.models_signals._update_level_and_orientation')
    @patch('ralph_assets.models_signals._update_localization')
    @patch('ralph_assets.models_signals._update_cached_localization')
    def test_update_core_localization(
        self, mock_update_cached_localization, mock_update_localization,
        mock_update_level_and_orientation,
    ):
        # case: ralph device doesn't exist
        self.dev_1.delete()
        update_core_localization(
            asset_dev_info=self.assets_dev_1.device_info,
        )
        self.assertFalse(mock_update_cached_localization.called)
        self.assertFalse(mock_update_localization.called)
        self.assertFalse(mock_update_level_and_orientation.called)
        # case: ralph device exists
        update_core_localization(
            asset_dev_info=self.assets_dev_2.device_info,
        )
        self.assertTrue(mock_update_cached_localization.called)
        self.assertTrue(mock_update_localization.called)
        self.assertTrue(mock_update_level_and_orientation.called)

    @patch('ralph_assets.models_signals.update_core_localization')
    def test_asset_device_info_post_save(self, mock):
        asset_device_info_post_save(
            sender=DeviceInfo, instance=self.assets_dev_2.device_info,
        )
        mock.assert_called_with(asset_dev_info=self.assets_dev_2.device_info)
