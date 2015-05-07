# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json

from django.core.cache import cache
from django.test import TestCase
from ralph.ui.tests.global_utils import UserFactory

from ralph_assets.tests.utils.assets import DCAssetFactory


class TestApi(TestCase):

    def setUp(self):
        self.user = UserFactory()
        self.api_login = {
            'format': 'json',
            'username': self.user.username,
            'api_key': self.user.api_key.key,
        }
        cache.delete("api_user_accesses")

    def get_response(self, resource='assets', data=None):
        path = "/assets/api/v0.9/{resource}/".format(resource=resource)
        if data:
            self.api_login.update(data)
        response = self.client.get(
            path=path, data=self.api_login, format='json',
        )
        self.assertEqual(response.status_code, 200)
        return response

    def resource_json(self, resource='assets', data=None):
        response = self.get_response(resource='assets', data=data)
        return json.loads(response.content)

    def test_asset_returned(self):
        asset = DCAssetFactory()
        data = {
            'id': asset.id,
        }
        api_result = self.resource_json('assets', data)
        for field in ['id', 'sn', 'barcode']:
            api_value = api_result['objects'][0][field]
            asset_value = getattr(asset, field)
            msg = 'field {}={!r} instead of {!r}'.format(
                field, api_value, asset_value,
            )
            self.assertEqual(api_value, asset_value, msg)

    def test_asset_found_by_valid_ralph_device_id(self):
        asset = DCAssetFactory()
        data = {
            'id': asset.id,
            'device_info__ralph_device__id': asset.device_info.ralph_device_id,
        }
        api_result = self.resource_json('assets', data)
        self.assertEqual(len(api_result['objects']), 1)
        self.assertEqual(api_result['objects'][0]['id'], asset.id)

    def test_asset_missing_by_invalid_ralph_device_id(self):
        asset = DCAssetFactory()
        asset2 = DCAssetFactory()
        invalid_ralph_device_id = asset2.device_info.ralph_device_id
        data = {
            'id': asset.id,
            'device_info__ralph_device__id': invalid_ralph_device_id,
        }
        api_result = self.resource_json('assets', data)
        self.assertEqual(len(api_result['objects']), 0)
