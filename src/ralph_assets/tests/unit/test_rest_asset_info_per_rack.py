# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from ralph_assets.models_assets import Orientation
from ralph_assets.rest.asset_info_per_rack import (
    TYPE_ACCESSORY,
    TYPE_ASSET,
)
from ralph_assets.tests.utils.assets import (
    AssetFactory,
    RackFactory,
    RackAccessoryFactory,
)


class TestRestAssetInfoPerRack(TestCase):
    def setUp(self):
        User.objects.create_superuser('test', 'test@test.test', 'test')
        self.client = APIClient()
        self.client.login(username='test', password='test')

        self.rack_1 = RackFactory(max_u_height=3)
        rack_2 = RackFactory()

        self.asset_1 = AssetFactory(
            device_info__position=1,
            device_info__slot_no='',
        )
        self.asset_2 = AssetFactory(
            device_info__position=2,
            device_info__slot_no='',
        )
        asset_3 = AssetFactory()

        self.rack_1.deviceinfo_set.add(self.asset_1.device_info)
        self.rack_1.deviceinfo_set.add(self.asset_2.device_info)
        rack_2.deviceinfo_set.add(asset_3.device_info)

        self.rack1_accessory = RackAccessoryFactory(
            rack=self.rack_1,
            server_room=self.rack_1.server_room,
            data_center=self.rack_1.server_room.data_center,
            orientation=Orientation.front,
        )
        self.rack2_accessory = RackAccessoryFactory(
            rack=rack_2,
            server_room=rack_2.server_room,
            data_center=rack_2.server_room.data_center,
            orientation=Orientation.front,
        )

    def tearDown(self):
        self.client.logout()

    def test_get(self):
        returned_json = json.loads(
            self.client.get(
                '/assets/api/rack/{0}/'.format(self.rack_1.id)
            ).content
        )
        self.maxDiff = None
        expected_json = {
            'info': {
                'id': self.rack_1.id,
                'name': self.rack_1.name,
                'data_center': self.rack_1.data_center.id,
                'server_room': self.rack_1.server_room.id,
                'max_u_height': self.rack_1.max_u_height,
                'visualization_col': self.rack_1.visualization_col,
                'visualization_row': self.rack_1.visualization_row,
                'free_u': self.rack_1.get_free_u(),
                'description': '{}'.format(self.rack_1.description),
                'orientation': '{}'.format(self.rack_1.get_orientation_desc())
            },
            'front': [
                {
                    '_type': TYPE_ASSET,
                    'id': self.asset_1.id,
                    'url': '{}'.format(self.asset_1.url),
                    'category': '{}'.format(self.asset_1.model.category),
                    'barcode': self.asset_1.barcode,
                    'sn': '{}'.format(self.asset_1.sn),
                    'height': float(self.asset_1.model.height_of_device),
                    'position': self.asset_1.device_info.position,
                    'model': self.asset_1.model.name,
                    'children': [],
                },
                {
                    '_type': TYPE_ASSET,
                    'id': self.asset_2.id,
                    'url': '{}'.format(self.asset_2.url),
                    'category': '{}'.format(self.asset_2.model.category),
                    'barcode': self.asset_2.barcode,
                    'sn': '{}'.format(self.asset_2.sn),
                    'height': float(self.asset_2.model.height_of_device),
                    'position': self.asset_2.device_info.position,
                    'model': self.asset_2.model.name,
                    'children': [],
                },
                {
                    '_type': TYPE_ACCESSORY,
                    'position': self.rack1_accessory.position,
                    'remarks': self.rack1_accessory.remarks,
                    'type': self.rack1_accessory.accessory.name,
                },
            ],
            'back': []
        }
        self.assertEquals(returned_json, expected_json)
