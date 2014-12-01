# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from ralph_assets.tests.utils.assets import RackFactory, AssetFactory


class TestRestAssetInfoPerRack(TestCase):
    def setUp(self):
        User.objects.create_superuser('test', 'test@test.test', 'test')
        self.client = APIClient()
        self.client.login(username='test', password='test')

        self.rack_1 = RackFactory()
        rack_2 = RackFactory()

        self.asset_1 = AssetFactory()
        self.asset_2 = AssetFactory()
        asset_3 = AssetFactory()

        self.rack_1.deviceinfo_set.add(self.asset_1.device_info)
        self.rack_1.deviceinfo_set.add(self.asset_2.device_info)
        rack_2.deviceinfo_set.add(asset_3.device_info)

    def tearDown(self):
        self.client.logout()

    def test_get(self):
        self.assertEquals(
            json.loads(
                self.client.get(
                    '/assets/api/rack/{0}/devices/'.format(self.rack_1.id)
                ).content
            ), {
                'status': True, 'data': [{
                    'asset_id': self.asset_1.id,
                    'url': self.asset_1.url,
                    'barcode': self.asset_1.barcode,
                    'sn': self.asset_1.sn,
                    'height_of_device': self.asset_1.model.height_of_device,
                    'position': self.asset_1.device_info.position,
                    'model': self.asset_1.model.name,
                }, {
                    'asset_id': self.asset_2.id,
                    'url': self.asset_2.url,
                    'barcode': self.asset_2.barcode,
                    'sn': self.asset_2.sn,
                    'height_of_device': self.asset_2.model.height_of_device,
                    'position': self.asset_2.device_info.position,
                    'model': self.asset_2.model.name,
                }]
            }
        )
